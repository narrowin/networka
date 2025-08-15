"""Textual app for selecting targets and actions.

First iteration focuses on selection only:
- Left pane: two tabs for Devices and Groups with multi-select lists
- Right pane: two tabs for Sequences and Commands
- Bottom bar: context help and key hints

Execution is not wired yet; we only collect selections and show a preview.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from network_toolkit.tui.data import TuiData


@dataclass
class SelectionState:
    devices: set[str]
    groups: set[str]
    sequences: set[str]
    # commands are free-form; collected via input
    command_text: str = ""


def run(config: str | Path = "config") -> None:
    """Entry to run the TUI app.

    Imports Textual at runtime to keep it an optional dependency.
    """
    try:  # pragma: no cover - UI framework import
        textual_app = importlib.import_module("textual.app")
        textual_binding = importlib.import_module("textual.binding")
        textual_containers = importlib.import_module("textual.containers")
        textual_widgets = importlib.import_module("textual.widgets")
        app_cls: Any = getattr(textual_app, "App")  # noqa: B009
        binding_cls: Any = getattr(textual_binding, "Binding")  # noqa: B009
        horizontal: Any = getattr(textual_containers, "Horizontal")  # noqa: B009
        vertical: Any = getattr(textual_containers, "Vertical")  # noqa: B009
        footer: Any = getattr(textual_widgets, "Footer")  # noqa: B009
        header: Any = getattr(textual_widgets, "Header")  # noqa: B009
        input_widget: Any = getattr(textual_widgets, "Input")  # noqa: B009
        static: Any = getattr(textual_widgets, "Static")  # noqa: B009
        tabbed_content: Any = getattr(textual_widgets, "TabbedContent")  # noqa: B009
        tab_pane: Any = getattr(textual_widgets, "TabPane")  # noqa: B009
        selection_list: Any = getattr(textual_widgets, "SelectionList")  # noqa: B009
        # Prefer RichLog; fall back to Log if not available in this Textual version
        try:
            text_log_cls: Any = getattr(textual_widgets, "RichLog")  # noqa: B009
        except AttributeError:
            text_log_cls = getattr(textual_widgets, "Log")  # noqa: B009
    except Exception as exc:  # pragma: no cover
        msg = "The TUI requires the 'textual' package. Install with: uv add textual or pip install textual"
        raise RuntimeError(msg) from exc

    data = TuiData(config)

    @dataclass
    class _State:
        devices: set[str]
        groups: set[str]
        sequences: set[str]
        command_text: str = ""

    state = _State(set(), set(), set(), "")

    # Note: Preview screen removed; we now show output in bottom TextLog

    class _App(app_cls):
        _errors: list[str]
        CSS = """
        #layout { height: 1fr; }
        #top { height: 1fr; }
        #bottom { height: 2fr; }
        #output-log { height: 1fr; border: round $accent; }
        #summary-panel { height: 7; }
        .panel Static.title { content-align: center middle; color: $secondary; }
        .panel { border: round $surface; padding: 1 1; }
        .pane-title { height: 3; content-align: center middle; text-style: bold; }
        .search { height: 3; }
        .scroll { height: 1fr; overflow: auto; }
        """
        BINDINGS: ClassVar[list[Any]] = [
            binding_cls("q", "quit", "Quit", show=True),
            binding_cls("enter", "confirm", "Run"),
            binding_cls("r", "confirm", "Run"),
            binding_cls("ctrl+c", "quit", "Quit"),
        ]

        def compose(self) -> Any:
            yield header(show_clock=True)
            with vertical(id="layout"):
                with horizontal(id="top"):
                    with vertical(classes="panel"):
                        yield static("Targets", classes="pane-title title")
                        with tabbed_content(id="targets-tabs"):
                            with tab_pane("Devices", id="tab-devices"):
                                yield input_widget(
                                    placeholder="Filter devices...",
                                    id="filter-devices",
                                    classes="search",
                                )
                                yield selection_list[str](
                                    *[(d, d, False) for d in data.targets().devices],
                                    id="list-devices",
                                    classes="scroll",
                                )
                            with tab_pane("Groups", id="tab-groups"):
                                yield input_widget(
                                    placeholder="Filter groups...",
                                    id="filter-groups",
                                    classes="search",
                                )
                                yield selection_list[str](
                                    *[(g, g, False) for g in data.targets().groups],
                                    id="list-groups",
                                    classes="scroll",
                                )
                    with vertical(classes="panel"):
                        yield static("Actions", classes="pane-title title")
                        with tabbed_content(id="actions-tabs"):
                            with tab_pane("Sequences", id="tab-sequences"):
                                yield input_widget(
                                    placeholder="Filter sequences...",
                                    id="filter-sequences",
                                    classes="search",
                                )
                                yield selection_list[str](
                                    *[(s, s, False) for s in data.actions().sequences],
                                    id="list-sequences",
                                    classes="scroll",
                                )
                            with tab_pane("Commands", id="tab-commands"):
                                yield input_widget(
                                    placeholder="Enter a command and press Enter to run",
                                    id="input-commands",
                                )
                        yield static("Press Enter to run", classes="title")
                        yield textual_widgets.Button("Run", id="run-button")
                with vertical(id="bottom"):
                    yield static("Status: idle", id="run-status")
                    with vertical(classes="panel", id="summary-panel"):
                        yield static("Summary", classes="pane-title title")
                        yield static("", id="run-summary")
                    with vertical(classes="panel"):
                        yield static("Output", classes="pane-title title")
                        yield text_log_cls(id="output-log", classes="scroll")
            yield footer()

        async def action_confirm(self) -> None:
            out_log = self.query_one("#output-log")
            if hasattr(out_log, "clear"):
                out_log.clear()
            # reset summary and any previous errors
            self._errors = []
            try:
                self.query_one("#run-summary").update("")
            except Exception:
                pass
            _log_write(out_log, "Starting run...")
            # Temporarily silence library logging to avoid background metadata
            logging.disable(logging.CRITICAL)
            try:
                self._collect_state()
                devices = await self._resolve_devices()
                if not devices:
                    self._render_summary("No devices selected.")
                    return
                plan = self._build_execution_plan(devices)
                if not plan:
                    self._render_summary("No sequences or commands provided.")
                    return
                # Update status and run with streaming
                total = len(plan)
                try:
                    self.query_one("#run-status").update(f"Status: running 0/{total}")
                except Exception:
                    pass
                summary = await self._run_plan(plan, out_log)
                # Update summary panel (include errors if any)
                try:
                    self._render_summary(summary)
                    self.query_one("#run-status").update("Status: idle")
                except Exception:
                    pass
            except Exception as e:  # noqa: BLE001
                self._render_summary(f"Run failed: {e}")
            finally:
                logging.disable(logging.NOTSET)

        async def on_input_submitted(self, event: Any) -> None:  # Textual Input submit
            # Only trigger when the commands input is submitted
            try:
                sender = (
                    getattr(event, "input", None)
                    or getattr(event, "control", None)
                    or getattr(event, "sender", None)
                )
                if getattr(sender, "id", "") == "input-commands":
                    await self.action_confirm()
                    if hasattr(event, "stop"):
                        event.stop()
            except Exception:
                # Best-effort; let Textual handle any event issues
                pass

        async def on_button_pressed(self, event: Any) -> None:
            try:
                btn = getattr(event, "button", None)
                if getattr(btn, "id", "") == "run-button":
                    await self.action_confirm()
                    if hasattr(event, "stop"):
                        event.stop()
            except Exception:
                pass

        def _collect_state(self) -> None:
            dev_list = self.query_one("#list-devices")
            grp_list = self.query_one("#list-groups")
            seq_list = self.query_one("#list-sequences")
            cmd_input = self.query_one("#input-commands")

            state.devices = self._selected_values(dev_list)
            state.groups = self._selected_values(grp_list)
            state.sequences = self._selected_values(seq_list)
            state.command_text = getattr(cmd_input, "value", "") or ""

        def _selected_values(self, sel: Any) -> set[str]:
            """Normalize selected items from a SelectionList to a set of strings."""
            # Prefer newer API if available
            if hasattr(sel, "selected_values"):
                try:
                    values = sel.selected_values
                    if values is not None:
                        return {str(v) for v in values}
                except Exception:
                    pass
            # Fallback to iterating over selected items which may be strings or option objects
            out: set[str] = set()
            try:
                for item in getattr(sel, "selected", []) or []:
                    val = getattr(item, "value", item)
                    out.add(str(val))
            except Exception:
                # Last resort: empty set on unexpected structure
                return set()
            return out

        async def _resolve_devices(self) -> list[str]:
            from network_toolkit.common.resolver import DeviceResolver

            resolver = DeviceResolver(data.config)
            selected: set[str] = set(state.devices)
            for g in state.groups:
                try:
                    for m in data.config.get_group_members(g):
                        selected.add(m)
                except Exception:  # pragma: no cover - non-critical
                    pass
            return [d for d in sorted(selected) if resolver.is_device(d)]

        def _build_execution_plan(self, devices: list[str]) -> dict[str, list[str]]:
            plan: dict[str, list[str]] = {}
            if state.sequences:
                for device in devices:
                    cmds: list[str] = []
                    for seq in sorted(state.sequences):
                        resolved = data.sequence_manager.resolve(seq, device) or []
                        cmds.extend(resolved)
                    if cmds:
                        plan[device] = cmds
            else:
                commands = list(_iter_commands(state.command_text))
                if commands:
                    for device in devices:
                        plan[device] = commands
            return plan

        async def _run_plan(
            self,
            plan: dict[str, list[str]],
            out_log: Any,
        ) -> str:
            sem = asyncio.Semaphore(5)
            total = len(plan)
            completed = 0
            successes = 0
            failures = 0

            async def run_device(device: str, commands: list[str]) -> tuple[str, bool]:
                async with sem:
                    ok = await asyncio.to_thread(
                        self._run_device_blocking_stream,
                        device,
                        commands,
                        out_log,
                    )
                    return device, ok

            tasks = [run_device(dev, cmds) for dev, cmds in plan.items()]
            for coro in asyncio.as_completed(tasks):
                _dev, ok = await coro
                completed += 1
                if ok:
                    successes += 1
                else:
                    failures += 1
                try:
                    self.query_one("#run-status").update(
                        f"Status: running {completed}/{total}"
                    )
                except Exception:
                    pass
            return f"Devices completed: {successes} succeeded, {failures} failed, total: {total}"

        def _run_device_blocking_stream(
            self,
            device: str,
            commands: list[str],
            out_log: Any,
        ) -> bool:
            ok = True
            try:
                from network_toolkit.cli import DeviceSession

                def out(msg: str) -> None:
                    try:
                        self.call_from_thread(_log_write, out_log, msg)
                    except Exception:
                        pass

                def err(msg: str) -> None:
                    try:
                        # record errors to be shown in summary later
                        self.call_from_thread(self._add_error, msg)
                    except Exception:
                        pass

                out(f"{device}: connecting...")
                with DeviceSession(device, data.config) as session:
                    out(f"{device}: connected")
                    for cmd in commands:
                        out(f"{device}$ {cmd}")
                        try:
                            raw = session.execute_command(cmd)
                            text = raw if type(raw) is str else str(raw)
                            out_strip = text.strip()
                            is_err = out_strip.upper().startswith(
                                "ERROR"
                            ) or out_strip.upper().startswith("FAIL")
                            target = err if is_err else out
                            if out_strip:
                                for line in text.rstrip().splitlines():
                                    target(line)
                            else:
                                target("<no output>")
                        except Exception as e:  # noqa: BLE001
                            ok = False
                            err(f"{device}: command error: {e}")
                out(f"{device}: done")
            except Exception as e:  # noqa: BLE001
                ok = False
                try:
                    self.call_from_thread(self._add_error, f"{device}: Failed: {e}")
                except Exception:
                    pass
            return ok

        def _add_error(self, msg: str) -> None:
            try:
                self._errors.append(str(msg))
            except Exception:
                self._errors = [str(msg)]

        def _render_summary(self, base_summary: str | None = None) -> None:
            try:
                errors: list[str] = getattr(self, "_errors", [])
            except Exception:
                errors = []
            parts: list[str] = []
            if base_summary:
                parts.append(base_summary)
            if errors:
                parts.append("Errors:")
                parts.extend(errors)
            text = "\n".join(parts)
            try:
                self.query_one("#run-summary").update(text)
            except Exception:
                pass

    def _iter_commands(text: str) -> Iterable[str]:
        for line in (text or "").splitlines():
            stripped = line.strip()
            if stripped:
                yield stripped

    def _log_write(log_widget: Any, message: str) -> None:
        try:
            msg = str(message)
            if hasattr(log_widget, "write"):
                log_widget.write(msg)
            elif hasattr(log_widget, "write_line"):
                log_widget.write_line(msg)
            elif hasattr(log_widget, "update"):
                # Fallback: append to existing content if possible
                try:
                    existing = getattr(log_widget, "renderable", "") or ""
                except Exception:
                    existing = ""
                content = f"{existing}\n{msg}" if existing else msg
                log_widget.update(content)
        except Exception:
            pass

    # Launch the app
    _App().run()
