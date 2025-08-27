"""TUI services layer.

Contains logic for resolving devices, building execution plans, and running
commands while streaming output via callbacks. This module is UI-framework
agnostic so it can be unit-tested without Textual.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.tui.data import TuiData
from network_toolkit.tui.models import (
    ExecutionPlan,
    RunCallbacks,
    RunResult,
    iter_commands,
)


class DeviceRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    device: str
    ok: bool


class ExecutionService:
    """Build plans and execute them with concurrency and streaming output."""

    def __init__(self, data: TuiData, *, concurrency: int = 5) -> None:
        self._data = data
        self._sem = asyncio.Semaphore(concurrency)

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

    async def run_plan(self, plan: ExecutionPlan, cb: RunCallbacks) -> RunResult:
        total = len(plan)
        completed = 0
        successes = 0
        failures = 0

        async def run_device(device: str, commands: list[str]) -> DeviceRunResult:
            async with self._sem:
                ok = await asyncio.to_thread(
                    self._run_device_blocking, device, commands, cb
                )
                return DeviceRunResult(device=device, ok=ok)

        tasks = [run_device(dev, cmds) for dev, cmds in plan.items()]
        for coro in asyncio.as_completed(tasks):
            res = await coro
            completed += 1
            if res.ok:
                successes += 1
            else:
                failures += 1
            cb.on_meta(f"progress: {completed}/{total}")
        return RunResult(total=total, successes=successes, failures=failures)

    def _run_device_blocking(
        self, device: str, commands: list[str], cb: RunCallbacks
    ) -> bool:
        ok = True
        try:
            # Import here to avoid making CLI a hard dependency of module import
            from network_toolkit.cli import DeviceSession

            cb.on_meta(f"{device}: connecting...")
            with DeviceSession(device, self._data.config) as session:
                cb.on_meta(f"{device}: connected")
                for cmd in commands:
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
        return ok
