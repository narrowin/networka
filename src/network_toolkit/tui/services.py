"""TUI services layer.

Contains logic for resolving devices, building execution plans, and running
commands while streaming output via callbacks. This module is UI-framework
agnostic so it can be unit-tested without Textual.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.tui.data import TuiData
from network_toolkit.tui.models import (
    CancellationToken,
    ExecutionPlan,
    RunCallbacks,
    RunResult,
    iter_commands,
)


class DeviceRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    device: str
    ok: bool
    output_lines: list[str]


class ExecutionService:
    """Build plans and execute them with concurrency and streaming output.

    Cancellation semantics:
    - Cooperative: ongoing device tasks periodically check the provided
      ``CancellationToken`` and bail between commands.
    - Bounded scheduling: only up to ``concurrency`` devices are scheduled at
      a time. When cancelled, we stop scheduling new devices so at most
      ``concurrency`` device tasks remain to finish.
    """

    def __init__(self, data: TuiData, *, concurrency: int = 5) -> None:
        self._data = data
        self._concurrency = max(1, int(concurrency))
        self._sem = asyncio.Semaphore(self._concurrency)
        # Track active sessions for hard-cancel support
        self._active_sessions: set[object] = set()
        self._active_lock = threading.Lock()

    # --- Hard-cancel support
    def _register_session(self, session: object) -> None:
        try:
            with self._active_lock:
                self._active_sessions.add(session)
        except Exception:
            pass

    def _unregister_session(self, session: object) -> None:
        try:
            with self._active_lock:
                self._active_sessions.discard(session)
        except Exception:
            pass

    def request_hard_cancel(self, cancel: CancellationToken | None = None) -> None:
        """Aggressively cancel by setting the token and closing active sessions.

        This will cause blocking reads/writes to error out and unwind quickly.
        Note: it does not revert server-side operations already in progress.
        """
        try:
            if cancel is not None:
                cancel.set()
        except Exception:
            pass
        sessions: list[object]
        try:
            with self._active_lock:
                sessions = list(self._active_sessions)
        except Exception:
            sessions = []
        for s in sessions:
            try:
                disc = getattr(s, "disconnect", None)
                if callable(disc):
                    disc()
            except Exception as e:
                logging.debug(f"Hard cancel disconnect failed: {e}")

    def resolve_devices(
        self, devices: Iterable[str], groups: Iterable[str]
    ) -> list[str]:
        """Resolve devices and expand groups using the project's resolver."""
        resolver = DeviceResolver(self._data.config)
        selected: set[str] = set(devices)
        for g in groups:
            try:
                for m in self._data.config.get_group_members(g):
                    selected.add(m)
            except Exception:
                # Best-effort, groups may be invalid during development
                logging.debug("Failed to expand group %s", g)
        return [d for d in sorted(selected) if resolver.is_device(d)]

    def build_plan(
        self, devices: Iterable[str], sequences: Iterable[str], command_text: str
    ) -> ExecutionPlan:
        plan: ExecutionPlan = {}
        seqs = list(sequences)
        if seqs:
            for device in devices:
                cmds: list[str] = []
                for seq in sorted(seqs):
                    resolved = self._data.sequence_manager.resolve(seq, device) or []
                    cmds.extend(resolved)
                if cmds:
                    plan[device] = cmds
        else:
            commands = list(iter_commands(command_text))
            if commands:
                for device in devices:
                    plan[device] = commands
        return plan

    async def run_plan(
        self,
        plan: ExecutionPlan,
        cb: RunCallbacks,
        *,
        cancel: CancellationToken | None = None,
    ) -> RunResult:
        total = len(plan)
        completed = 0
        successes = 0
        failures = 0
        results_by_device: dict[str, DeviceRunResult] = {}

        # If cancellation was requested before any work starts, record per-device
        # cancelled results and return immediately.
        if cancel and cancel.is_set():
            for dev in plan.keys():
                try:
                    cb.on_meta(f"{dev}: cancelled before start")
                except Exception:
                    pass
                results_by_device[dev] = DeviceRunResult(
                    device=dev,
                    ok=False,
                    output_lines=[f"{dev}: cancelled before start"],
                )
                failures += 1
            # Do not emit buffered outputs on pre-start cancel; return summary only
            return RunResult(total=total, successes=successes, failures=failures)

        async def run_device(device: str, commands: list[str]) -> DeviceRunResult:
            async with self._sem:
                if cancel and cancel.is_set():
                    # Inform callbacks that we cancelled this device before starting
                    try:
                        cb.on_meta(f"{device}: cancelled before start")
                    except Exception:
                        pass
                    return DeviceRunResult(
                        device=device,
                        ok=False,
                        output_lines=[f"{device}: cancelled before start"],
                    )
                # Call into blocking runner, accommodating older test monkeypatches
                from typing import Any, cast

                def _invoke() -> Any:
                    try:
                        return self._run_device_blocking(device, commands, cb, cancel)
                    except TypeError:
                        # Back-compat for tests that monkeypatch a 3-param function
                        return self._run_device_blocking(device, commands, cb)

                result = await asyncio.to_thread(_invoke)
                # _run_device_blocking may return DeviceRunResult (new) or bool (tests)
                if hasattr(result, "device") and hasattr(result, "output_lines"):
                    return cast(DeviceRunResult, result)
                return DeviceRunResult(device=device, ok=bool(result), output_lines=[])

        # Schedule lazily up to concurrency; stop scheduling once cancelled
        items = list(plan.items())
        idx = 0
        active: set[asyncio.Task[DeviceRunResult]] = set()

        def _schedule_next() -> None:
            nonlocal idx
            while (
                idx < len(items)
                and len(active) < self._concurrency
                and not (cancel and cancel.is_set())
            ):
                dev, cmds = items[idx]
                idx += 1
                active.add(asyncio.create_task(run_device(dev, cmds)))

        _schedule_next()
        while active:
            done, pending = await asyncio.wait(
                active, return_when=asyncio.FIRST_COMPLETED
            )
            for t in done:
                try:
                    res = t.result()
                except Exception as e:
                    # Treat unexpected task failure as a device failure
                    failures += 1
                    logging.debug("device task failed: %s", e)
                    continue
                completed += 1
                if res.ok:
                    successes += 1
                else:
                    failures += 1
                results_by_device[res.device] = res
                cb.on_meta(f"progress: {completed}/{total}")
            active = set(pending)
            if cancel and cancel.is_set():
                cb.on_meta("cancellation requested; stopping scheduling")
                # Do not schedule any new work; allow current active tasks to finish
            else:
                _schedule_next()
        # Emit any buffered outputs from tasks that didn't stream directly
        for dev in plan.keys():
            r = results_by_device.get(dev)
            if not r:
                continue
            for line in r.output_lines:
                cb.on_output(line)
        return RunResult(total=total, successes=successes, failures=failures)

    def _run_device_blocking(
        self,
        device: str,
        commands: list[str],
        cb: RunCallbacks,
        cancel: CancellationToken | None = None,
    ) -> DeviceRunResult:
        ok = True
        # Collect output lines for return (not emitted here); we stream per-command chunks
        buf: list[str] = []
        try:
            # Import here to avoid making CLI a hard dependency of module import
            from network_toolkit.cli import DeviceSession

            cb.on_meta(f"{device}: connecting...")
            if cancel and cancel.is_set():
                cb.on_meta(f"{device}: cancelled before connect")
                return DeviceRunResult(device=device, ok=False, output_lines=buf)
            with DeviceSession(device, self._data.config) as session:
                # Make this session visible for hard-cancel
                try:
                    self._register_session(session)
                except Exception:
                    pass
                cb.on_meta(f"{device}: connected")
                for cmd in commands:
                    if cancel and cancel.is_set():
                        cb.on_meta(f"{device}: cancelled")
                        ok = False
                        break
                    # Build a per-command chunk: header with device & command, raw output lines, then a footer
                    header = f"-- {device}: {cmd} --"
                    footer = f"-- finish {device}: {cmd} --"
                    cb.on_meta(f"{device}$ {cmd}")
                    try:
                        raw = session.execute_command(cmd)
                        text = raw if isinstance(raw, str) else str(raw)
                        out_strip = text.strip()
                        if out_strip:
                            for line in text.rstrip().splitlines():
                                cb.on_output(line)
                    except Exception as e:
                        ok = False
                        cb.on_error(f"{device}: command error: {e}")
            cb.on_meta(f"{device}: done")
        except Exception as e:
            ok = False
            cb.on_error(f"{device}: Failed: {e}")
        # Return whatever we collected (may be empty) on failure
        return DeviceRunResult(device=device, ok=ok, output_lines=[])
