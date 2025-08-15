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
        CSS = """
        #layout { height: 1fr; }
        #top { height: 1fr; }
        #output-log { height: 1fr; border: round $accent; }
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
                yield text_log_cls(id="output-log")
            yield footer()

        async def action_confirm(self) -> None:
            self._collect_state()
            log = self.query_one("#output-log")
            if hasattr(log, "clear"):
                log.clear()
            devices = await self._resolve_devices()
            if not devices:
                _log_write(log, "No devices selected.")
                return
            plan = self._build_execution_plan(devices)
            if not plan:
                _log_write(log, "No sequences or commands provided.")
                return
            await self._run_plan(plan, log)

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

        async def _run_plan(self, plan: dict[str, list[str]], log: Any) -> None:
            sem = asyncio.Semaphore(5)

            async def run_device(
                device: str, commands: list[str]
            ) -> tuple[str, list[tuple[str, str]] | str]:
                async with sem:
                    return await asyncio.to_thread(
                        self._run_device_blocking, device, commands
                    )

            tasks = [run_device(dev, cmds) for dev, cmds in plan.items()]
            for coro in asyncio.as_completed(tasks):
                device, result = await coro
                if isinstance(result, str):
                    _log_write(log, f"[red]{device}: {result}[/red]")
                else:
                    _log_write(
                        log, f"[bold]{device}[/bold]: executed {len(result)} command(s)"
                    )
                    for cmd, out in result:
                        _log_write(log, f"[cyan]{device}[/cyan]$ {cmd}")
                        if out.strip():
                            for line in out.rstrip().splitlines():
                                _log_write(log, line)
                        else:
                            _log_write(log, "<no output>")

        def _run_device_blocking(
            self, device: str, commands: list[str]
        ) -> tuple[str, list[tuple[str, str]] | str]:
            try:
                from network_toolkit.cli import DeviceSession

                results: list[tuple[str, str]] = []
                with DeviceSession(device, data.config) as session:
                    for cmd in commands:
                        try:
                            out = session.execute_command(cmd)
                        except Exception as e:  # noqa: BLE001
                            out = f"ERROR: {e}"
                        results.append((cmd, out))
                return device, results
            except Exception as e:  # noqa: BLE001
                return device, f"Failed: {e}"

    def _iter_commands(text: str) -> Iterable[str]:
        for raw in text.splitlines():
            cmd = raw.strip()
            if cmd:
                yield cmd

    def _log_write(log_widget: Any, message: str) -> None:
        """Write a line to either RichLog or Log widgets."""
        # RichLog has write(), Log has write_line(); both may have clear()
        if hasattr(log_widget, "write"):
            log_widget.write(message)
        elif hasattr(log_widget, "write_line"):
            log_widget.write_line(message)
        else:
            # Fallback: attempt to update content if possible
            try:
                current = getattr(log_widget, "renderable", "")
                new = f"{current}\n{message}" if current else message
                log_widget.update(new)
            except Exception:
                pass

    _App().run()
