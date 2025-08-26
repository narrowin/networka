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
import threading
import time
from pathlib import Path
from typing import Any, ClassVar

from network_toolkit.tui.data import TuiData
from network_toolkit.tui.helpers import log_write
from network_toolkit.tui.models import RunCallbacks, SelectionState
from network_toolkit.tui.services import ExecutionService


def _new_rich_text() -> Any:  # pragma: no cover - optional rich dependency helper
    try:
        from rich.text import Text

        return Text()
    except Exception:
        return None

    # models.SelectionState is used instead of local dataclass


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

    # Helper to construct bindings with compatibility across Textual versions
    def _mk_binding(
        key: str,
        action: str,
        desc: str,
        *,
        show: bool = False,
        key_display: str | None = None,
        priority: bool = False,
    ) -> Any:
        try:
            return binding_cls(key, action, desc, show, key_display, priority)
        except TypeError:
            try:
                return binding_cls(key, action, desc, show)
            except TypeError:
                return binding_cls(key, action)

    # Use shared SelectionState model for state
    state = SelectionState(
        devices=set(), groups=set(), sequences=set(), command_text=""
    )
    # Services layer for plan building and execution
    service = ExecutionService(data)

    # Note: Preview screen removed; we now show output in bottom TextLog

    class _App(app_cls):
        _errors: list[str]
        _meta: list[str]
        CSS = """
        #layout { height: 1fr; }
        #top { height: 1fr; }
    #bottom { height: auto; }
    #bottom.expanded { height: 3fr; }
    #output-log { height: 1fr; }
    #summary-panel { height: 1fr; }
        .hidden { display: none; }
        #top > .panel { height: 1fr; }
        .panel Static.title { content-align: center middle; color: $secondary; }
        .panel { border: round $surface; padding: 1 1; }
        .pane-title { height: 3; content-align: center middle; text-style: bold; }
        .search { height: 3; }
        .scroll { height: 1fr; overflow: auto; }
    /* Improve visibility of selected items (full-line) in SelectionList */
    /* Cover multiple Textual versions/states (class-based only) */
    SelectionList .selected,
        SelectionList .is-selected,
        SelectionList .option--selected,
        SelectionList .selection-list--option--selected,
        SelectionList *.-selected,
        SelectionList *.-highlight,
        SelectionList .selection-list--option.-selected,
        SelectionList .selection-list--option.--selected,
        #list-devices .selected,
        #list-devices .is-selected,
        #list-devices .option--selected,
        #list-devices .selection-list--option--selected,
        #list-devices *.-selected,
        #list-devices *.-highlight,
        #list-devices .selection-list--option.-selected,
        #list-devices .selection-list--option.--selected,
        #list-groups .selected,
        #list-groups .is-selected,
        #list-groups .option--selected,
        #list-groups .selection-list--option--selected,
        #list-groups *.-selected,
        #list-groups *.-highlight,
        #list-groups .selection-list--option.-selected,
        #list-groups .selection-list--option.--selected,
        #list-sequences .selected,
        #list-sequences .is-selected,
        #list-sequences .option--selected,
        #list-sequences .selection-list--option--selected,
        #list-sequences *.-selected,
        #list-sequences *.-highlight,
        #list-sequences .selection-list--option.-selected,
        #list-sequences .selection-list--option.--selected {
            background: #0057d9;
            color: #ffffff;
            text-style: bold;
        }
        """
        BINDINGS: ClassVar[list[Any]] = [
            _mk_binding("q", "quit", "Quit", show=True),
            _mk_binding("enter", "confirm", "Run"),
            _mk_binding("r", "confirm", "Run"),
            _mk_binding("ctrl+c", "quit", "Quit"),
            # Make toggles priority so they work even while typing or during runs
            _mk_binding("s", "toggle_summary", "Summary", show=True, priority=True),
            _mk_binding("o", "toggle_output", "Output", show=True, priority=True),
            _mk_binding("f", "focus_filter", "Focus filter", show=True, priority=True),
            _mk_binding("t", "toggle_theme", "Theme", show=True, priority=True),
            _mk_binding("f2", "toggle_summary", "Summary"),
            # Copy helpers
            _mk_binding(
                "y", "copy_last_error", "Copy last error", show=True, priority=True
            ),
            _mk_binding(
                "ctrl+y", "copy_status", "Copy status", show=True, priority=True
            ),
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
                                # Create empty list; we'll populate in on_mount for compatibility
                                yield selection_list(
                                    id="list-devices",
                                    classes="scroll",
                                )
                            with tab_pane("Groups", id="tab-groups"):
                                yield input_widget(
                                    placeholder="Filter groups...",
                                    id="filter-groups",
                                    classes="search",
                                )
                                yield selection_list(
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
                                yield selection_list(
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
                    with vertical(classes="panel hidden", id="summary-panel"):
                        yield static("Summary", classes="pane-title title")
                        yield text_log_cls(id="run-summary", classes="scroll")
                        yield input_widget(
                            placeholder="Filter summary...",
                            id="filter-summary",
                            classes="search",
                        )
                    with vertical(classes="panel hidden", id="output-panel"):
                        yield static("Output", classes="pane-title title")
                        yield text_log_cls(id="output-log", classes="scroll")
                        yield input_widget(
                            placeholder="Filter output...",
                            id="filter-output",
                            classes="search",
                        )
            yield footer()

        async def on_mount(self) -> None:  # Populate lists after UI mounts
            try:
                t = data.targets()
                a = data.actions()
                # Keep base lists for filtering
                self._all_devices = list(t.devices)
                self._all_groups = list(t.groups)
                self._all_sequences = list(a.sequences)
                self._populate_selection_list("list-devices", self._all_devices)
                self._populate_selection_list("list-groups", self._all_groups)
                self._populate_selection_list("list-sequences", self._all_sequences)
            except Exception:
                pass
            # Brief startup notice that this TUI is a prototype/WIP
            try:
                msg = (
                    "Prototype: This TUI is a work in progress — expect rough edges."
                )
                try:
                    # Prefer modern Textual notify API with severity & timeout
                    self.notify(msg, timeout=3, severity="warning")  # type: ignore[arg-type]
                except TypeError:
                    # Older Textual: severity param may not exist
                    self.notify(msg, timeout=3)  # type: ignore[misc]
                except AttributeError:
                    # Fallback: temporarily show in status bar and restore after delay
                    try:
                        status = self.query_one("#run-status")
                        # Save and restore prior content
                        try:
                            prev_text = getattr(getattr(status, "renderable", None), "plain", None) or "Status: idle"
                        except Exception:
                            prev_text = "Status: idle"
                        try:
                            status.update(msg)
                        except Exception:
                            pass
                        try:
                            # Use App timer if available
                            self.set_timer(3.0, lambda: status.update(prev_text))  # type: ignore[attr-defined]
                        except Exception:
                            # Best-effort async sleep & restore
                            async def _restore() -> None:
                                try:
                                    await asyncio.sleep(3)
                                    status.update(prev_text)
                                except Exception:
                                    pass
                            try:
                                self.call_later(_restore)  # type: ignore[attr-defined]
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
            # Record UI thread identity for safe callback dispatching
            try:
                self._ui_thread_ident = threading.get_ident()
            except Exception:
                self._ui_thread_ident = None
            # Internal state for user toggling of summary
            self._summary_user_hidden = False
            # Internal state for user toggling of output
            self._output_user_hidden = False
            # Track whether a run is currently active
            self._run_active = False
            # Theme
            try:
                self._dark_mode = bool(getattr(self, "dark", True))
            except Exception:
                self._dark_mode = True
            # Filters state
            self._summary_filter = ""
            self._output_filter = ""
            # Output lines buffer for filtering
            self._output_lines: list[str] = []
            # Hide bottom area initially if no summary/output and idle status
            self._refresh_bottom_visibility()

        async def on_input_changed(self, event: Any) -> None:  # Textual Input change
            """Live-filter lists and logs based on associated input widgets."""
            try:
                sender = (
                    getattr(event, "input", None)
                    or getattr(event, "control", None)
                    or getattr(event, "sender", None)
                )
                sender_id = getattr(sender, "id", "") or ""
                value = getattr(sender, "value", "") or ""
            except Exception:
                return
            text = value.strip().lower()
            # Devices filter
            if sender_id == "filter-devices":
                base: list[str] = list(getattr(self, "_all_devices", []) or [])
                try:
                    sel_widget = self.query_one("#list-devices")
                    current_sel: set[str] = self._selected_values(sel_widget)
                except Exception:
                    current_sel = set()
                items = [d for d in base if text in d.lower()]
                self._populate_selection_list(
                    "list-devices", items, selected=current_sel
                )
                return
            # Groups filter
            if sender_id == "filter-groups":
                base = list(getattr(self, "_all_groups", []) or [])
                try:
                    sel_widget = self.query_one("#list-groups")
                    current_sel = self._selected_values(sel_widget)
                except Exception:
                    current_sel = set()
                items = [g for g in base if text in g.lower()]
                self._populate_selection_list(
                    "list-groups", items, selected=current_sel
                )
                return
            # Sequences filter
            if sender_id == "filter-sequences":
                base = list(getattr(self, "_all_sequences", []) or [])
                try:
                    sel_widget = self.query_one("#list-sequences")
                    current_sel = self._selected_values(sel_widget)
                except Exception:
                    current_sel = set()
                items = [s for s in base if text in s.lower()]
                self._populate_selection_list(
                    "list-sequences", items, selected=current_sel
                )
                return
            # Summary filter
            if sender_id == "filter-summary":
                try:
                    self._summary_filter = value
                except Exception:
                    self._summary_filter = value
                # Re-render summary in-place
                self._render_summary()
                return
            # Output filter
            if sender_id == "filter-output":
                try:
                    self._output_filter = value
                except Exception:
                    self._output_filter = value
                # Re-render output log from buffer
                try:
                    out_log = self.query_one("#output-log")
                except Exception:
                    out_log = None
                if out_log is not None:
                    try:
                        if hasattr(out_log, "clear"):
                            out_log.clear()
                    except Exception:
                        pass
                    filt = (value or "").strip().lower()
                    for line in getattr(self, "_output_lines", []) or []:
                        if not filt or (filt in line.lower()):
                            log_write(out_log, line)
                return

        async def action_confirm(self) -> None:
            out_log = self.query_one("#output-log")
            if hasattr(out_log, "clear"):
                out_log.clear()
            # reset buffered output lines for fresh run
            try:
                self._output_lines = []
            except Exception:
                pass
            # reset summary and any previous errors
            self._errors = []
            self._meta = []
            start_ts: float | None = None
            try:
                self.query_one("#run-summary").update("")
                self._hide_summary_panel()
                self._hide_output_panel()
            except Exception:
                pass
            self._add_meta("Starting run...")
            # Temporarily silence library logging to avoid background metadata
            logging.disable(logging.CRITICAL)
            try:
                # Mark run active and disable inputs & run button to avoid focus capture
                self._run_active = True
                self._set_inputs_enabled(False)
                self._set_run_enabled(False)
                start_ts = time.monotonic()
                self._collect_state()
                devices = await asyncio.to_thread(
                    service.resolve_devices, state.devices, state.groups
                )
                if not devices:
                    self._render_summary("No devices selected.")
                    try:
                        msg = "Status: idle — No devices selected."
                        self.query_one("#run-status").update(msg)
                        self._refresh_bottom_visibility()
                    except Exception:
                        pass
                    return
                plan = service.build_plan(devices, state.sequences, state.command_text)
                if not plan:
                    self._render_summary("No sequences or commands provided.")
                    try:
                        msg = "Status: idle — No sequences or commands provided."
                        self.query_one("#run-status").update(msg)
                        self._refresh_bottom_visibility()
                    except Exception:
                        pass
                    return
                # Update status and run with streaming
                total = len(plan)
                try:
                    self._show_bottom_panel()
                    self.query_one("#run-status").update(f"Status: running 0/{total}")
                except Exception:
                    pass
                summary_result = await service.run_plan(
                    plan,
                    RunCallbacks(
                        on_output=lambda m: self._dispatch_ui(self._output_append, m),
                        on_error=lambda m: self._dispatch_ui(self._add_error, m),
                        on_meta=lambda m: self._dispatch_ui(self._add_meta, m),
                    ),
                )
                # Update summary panel (include errors if any)
                try:
                    # If any output lines were collected, ensure the output panel is visible
                    if getattr(self, "_output_lines", None):
                        self._show_output_panel()
                        # Repaint output from buffer to avoid empty view due to race
                        try:
                            out_log = self.query_one("#output-log")
                            if hasattr(out_log, "clear"):
                                out_log.clear()
                            filt = (
                                (getattr(self, "_output_filter", "") or "")
                                .strip()
                                .lower()
                            )
                            for line in self._output_lines:
                                if not filt or (filt in line.lower()):
                                    log_write(out_log, line)
                        except Exception:
                            pass
                    elapsed = time.monotonic() - start_ts
                    summary_with_time = (
                        f"{summary_result.human_summary()} (duration: {elapsed:.2f}s)"
                    )
                    self._render_summary(summary_with_time)
                    # Reflect summary on the status line; hint about errors if present
                    err_count = 0
                    try:
                        err_count = len(getattr(self, "_errors", []) or [])
                    except Exception:
                        err_count = 0
                    status_msg = f"Status: idle — {summary_with_time}"
                    if err_count:
                        status_msg += " — errors available (press s)"
                    self.query_one("#run-status").update(status_msg)
                    self._refresh_bottom_visibility()
                except Exception:
                    pass
            except Exception as e:  # noqa: BLE001
                try:
                    elapsed = (
                        (time.monotonic() - start_ts) if (start_ts is not None) else 0.0
                    )
                except Exception:
                    elapsed = 0.0
                self._render_summary(f"Run failed: {e} (after {elapsed:.2f}s)")
                try:
                    self.query_one("#run-status").update(
                        f"Status: idle — Run failed: {e}"
                    )
                    # If partial output exists, show it
                    if getattr(self, "_output_lines", None):
                        self._show_output_panel()
                    self._refresh_bottom_visibility()
                except Exception:
                    pass
            finally:
                logging.disable(logging.NOTSET)
                # Re-enable controls after run
                try:
                    self._run_active = False
                    self._set_inputs_enabled(True)
                    self._set_run_enabled(True)
                except Exception:
                    pass

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

        def _dispatch_ui(self, fn: Any, *args: Any, **kwargs: Any) -> None:
            """Invoke a UI-mutating function safely from any thread.

            If called from the UI thread, call directly. Otherwise, use
            call_from_thread when available. Fallback to direct call.
            """
            # Prefer scheduling via call_from_thread when available to ensure UI paints
            try:
                if hasattr(self, "call_from_thread"):
                    self.call_from_thread(fn, *args, **kwargs)
                    return
            except Exception:
                pass
            # Fallback: attempt direct call
            try:
                fn(*args, **kwargs)
            except Exception as exc:
                logging.debug(f"UI dispatch failed: {exc}")

        def on_key(self, event: Any) -> None:
            """Global key fallback to ensure toggles work even if focus is on inputs."""
            try:
                key = str(getattr(event, "key", "")).lower()
            except Exception:
                key = ""
            if key == "s":
                try:
                    self.action_toggle_summary()
                    if hasattr(event, "stop"):
                        event.stop()
                except Exception:
                    pass
            elif key == "o":
                try:
                    self.action_toggle_output()
                    if hasattr(event, "stop"):
                        event.stop()
                except Exception:
                    pass
            elif key == "t":
                try:
                    self.action_toggle_theme()
                    if hasattr(event, "stop"):
                        event.stop()
                except Exception:
                    pass
            elif key == "f":
                try:
                    self.action_focus_filter()
                    if hasattr(event, "stop"):
                        event.stop()
                except Exception:
                    pass
            elif key == "y":
                try:
                    self.action_copy_last_error()
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

        def _populate_selection_list(
            self,
            widget_id: str,
            items: list[str],
            *,
            selected: set[str] | None = None,
        ) -> None:
            """Populate a SelectionList with best-effort API compatibility across Textual versions.

            If `selected` is provided, best-effort pre-select those values.
            """
            try:
                sel = self.query_one(f"#{widget_id}")
            except Exception:
                return

            # Clear existing options
            for method in ("clear_options", "clear"):
                if hasattr(sel, method):
                    try:
                        getattr(sel, method)()
                        break
                    except Exception:
                        pass

            # Try bulk add first
            if hasattr(sel, "add_options"):
                sel_set = selected or set()
                opts_variants: list[list[object]] = [
                    [(label, label, (label in sel_set)) for label in items],
                    [(label, label) for label in items],
                    list(items),
                ]
                for opts in opts_variants:
                    try:
                        sel.add_options(opts)
                        # Some variants ignore selection; enforce afterwards if needed
                        if selected:
                            self._try_apply_selection(sel, selected)
                        return
                    except Exception as exc:
                        logging.debug(f"add_options variant failed: {exc}")

            # Fallback to adding one by one with different signatures
            if hasattr(sel, "add_option"):
                for label in items:
                    added = False
                    for args in (
                        (label, label, (selected is not None and label in selected)),
                        (label, label),
                        (label,),
                        ((label, label, False),),
                        ((label, label),),
                    ):
                        try:
                            sel.add_option(*args)
                            added = True
                            break
                        except Exception as exc:
                            logging.debug(f"add_option signature failed: {exc}")
                    if not added:
                        # Last resort: try 'append' of an option-like tuple
                        try:
                            if hasattr(sel, "append"):
                                sel.append(
                                    (
                                        label,
                                        label,
                                        (selected is not None and label in selected),
                                    )
                                )
                        except Exception as exc:
                            logging.debug(f"append to selection list failed: {exc}")
                # Enforce selection afterwards
                if selected:
                    self._try_apply_selection(sel, selected)

        def _try_apply_selection(self, sel: Any, selected: set[str]) -> None:
            """Best-effort to set selected values on a SelectionList across versions."""
            try:
                if hasattr(sel, "set_value"):
                    sel.set_value(list(selected))
                    return
            except Exception:
                pass
            try:
                if hasattr(sel, "selected") and isinstance(sel.selected, list):
                    sel.selected = list(selected)
                    return
            except Exception as exc:
                logging.debug(f"Direct selected assignment failed: {exc}")
            # Fallback: toggle/select by value methods
            for val in selected:
                for method in ("select", "select_by_value", "toggle_value"):
                    if hasattr(sel, method):
                        try:
                            getattr(sel, method)(val)
                            break
                        except Exception as exc:
                            logging.debug(f"Selecting value via {method} failed: {exc}")

        # Device resolution, plan building, and execution handled by services layer

        def _add_error(self, msg: str) -> None:
            try:
                self._errors.append(str(msg))
            except Exception:
                self._errors = [str(msg)]
            # refresh summary live
            try:
                self._render_summary()
            except Exception:
                pass

        def _render_summary(self, base_summary: str | None = None) -> None:
            try:
                errors: list[str] = getattr(self, "_errors", [])
            except Exception:
                errors = []
            try:
                meta: list[str] = getattr(self, "_meta", [])
            except Exception:
                meta = []
            renderable: Any = None
            # If a filter is active, compile plain text and filter lines for simplicity
            filt = (getattr(self, "_summary_filter", "") or "").strip().lower()
            if filt:
                lines: list[str] = []
                if base_summary:
                    lines.append(base_summary)
                # Info first
                if meta:
                    lines.append("Info:")
                    lines.extend([f" • {m}" for m in meta])
                # Errors at the bottom
                if errors:
                    lines.append("Errors:")
                    lines.extend([f" • {e}" for e in errors])
                filtered = [ln for ln in lines if filt in ln.lower()]
                renderable = "\n".join(filtered)
            else:
                # Try to build a Rich Text for styled output (errors in red)
                try:
                    rich_text = _new_rich_text()
                    if rich_text is not None:
                        first = True
                        if base_summary:
                            rich_text.append(base_summary)
                            first = False
                        if meta:
                            if not first:
                                rich_text.append("\n")
                            rich_text.append("Info:", style="bold")
                            for m in meta:
                                rich_text.append("\n • ")
                                rich_text.append(str(m))
                            first = False
                        if errors:
                            if not first:
                                rich_text.append("\n")
                            rich_text.append("Errors:", style="bold")
                            for err in errors:
                                rich_text.append("\n • ")
                                rich_text.append(str(err), style="red")
                        renderable = rich_text
                except Exception:
                    renderable = None
            if renderable is None:
                # Fallback to plain text without styling
                parts: list[str] = []
                if base_summary:
                    parts.append(base_summary)
                if meta:
                    parts.append("Info:")
                    parts.extend([f" • {m}" for m in meta])
                if errors:
                    parts.append("Errors:")
                    parts.extend([f" • {e}" for e in errors])
                renderable = "\n".join(parts)
            try:
                widget = self.query_one("#run-summary")
            except Exception:
                widget = None
            if widget is not None:
                try:
                    # Clear previous content if it's a Log-like widget
                    if hasattr(widget, "clear"):
                        widget.clear()
                except Exception:
                    pass
                try:
                    if hasattr(widget, "update"):
                        widget.update(renderable)
                    elif hasattr(widget, "write"):
                        text = str(renderable)
                        for line in text.splitlines():
                            widget.write(line)
                    else:
                        # Last resort
                        widget.update(str(renderable))
                except Exception:
                    pass
            # Auto-show summary only when there are errors; otherwise keep user control
            should_show = bool(errors)
            if should_show and not getattr(self, "_summary_user_hidden", False):
                self._show_summary_panel()

        def _add_meta(self, msg: str) -> None:
            try:
                self._meta.append(str(msg))
            except Exception:
                self._meta = [str(msg)]
            # refresh summary live
            try:
                self._render_summary()
            except Exception:
                pass

        def _output_append(self, msg: str) -> None:
            """Append a line to the output log honoring the current output filter."""
            try:
                text = str(msg)
            except Exception:
                text = f"{msg}"
            # Show output panel on first output unless user hid it
            try:
                self._maybe_show_output_panel()
            except Exception:
                pass
            try:
                self._output_lines.append(text)
            except Exception:
                self._output_lines = [text]
            # Re-render depending on filter
            try:
                out_log = self.query_one("#output-log")
            except Exception:
                out_log = None
            if out_log is None:
                return
            filt = (getattr(self, "_output_filter", "") or "").strip().lower()
            if filt:
                try:
                    if hasattr(out_log, "clear"):
                        out_log.clear()
                except Exception:
                    pass
                for line in self._output_lines:
                    if filt in line.lower():
                        log_write(out_log, line)
            else:
                log_write(out_log, text)

        def _show_output_panel(self) -> None:
            try:
                panel = self.query_one("#output-panel")
            except Exception:
                return
            try:
                panel.remove_class("hidden")
            except Exception:
                try:
                    styles = getattr(panel, "styles", None)
                    if styles and hasattr(styles, "display"):
                        styles.display = "block"
                except Exception:
                    pass
            self._refresh_bottom_visibility()

        def _hide_output_panel(self) -> None:
            try:
                panel = self.query_one("#output-panel")
            except Exception:
                return
            try:
                panel.add_class("hidden")
            except Exception:
                try:
                    styles = getattr(panel, "styles", None)
                    if styles and hasattr(styles, "display"):
                        styles.display = "none"
                except Exception:
                    pass
            self._refresh_bottom_visibility()

        def _maybe_show_output_panel(self) -> None:
            """Show output panel only if user hasn't hidden it explicitly."""
            if not getattr(self, "_output_user_hidden", False):
                self._show_output_panel()

        def action_toggle_summary(self) -> None:
            """Toggle visibility of the summary panel."""
            try:
                panel = self.query_one("#summary-panel")
            except Exception:
                return
            # Determine if currently hidden via 'hidden' class
            try:
                classes: set[str] = set(getattr(panel, "classes", []) or [])
            except Exception:
                classes = set()
            is_hidden = "hidden" in classes
            if is_hidden:
                # User explicitly wants to see it; clear the hidden flag
                self._summary_user_hidden = False
                # Always show when user toggles on, regardless of current content
                self._show_summary_panel()
            else:
                # User hides the panel; set the flag and hide
                self._summary_user_hidden = True
                self._hide_summary_panel()
                self._refresh_bottom_visibility()

        def action_toggle_output(self) -> None:
            """Toggle visibility of the output panel."""
            try:
                panel = self.query_one("#output-panel")
            except Exception:
                return
            try:
                classes: set[str] = set(getattr(panel, "classes", []) or [])
            except Exception:
                classes = set()
            is_hidden = "hidden" in classes
            if is_hidden:
                self._output_user_hidden = False
                # Always show when user toggles on
                self._show_output_panel()
            else:
                self._output_user_hidden = True
                self._hide_output_panel()
                self._refresh_bottom_visibility()

        def _set_inputs_enabled(self, enabled: bool) -> None:
            """Enable/disable search and command inputs during a run to avoid key capture."""
            ids = [
                "#filter-devices",
                "#filter-groups",
                "#filter-sequences",
                "#filter-summary",
                "#filter-output",
                "#input-commands",
            ]
            for wid in ids:
                try:
                    w = self.query_one(wid)
                except Exception:
                    w = None
                if w is None:
                    continue
                # Prefer 'disabled' attribute when available
                try:
                    if hasattr(w, "disabled"):
                        w.disabled = not enabled
                    elif hasattr(w, "can_focus"):
                        w.can_focus = enabled
                except Exception:
                    pass

        def _set_run_enabled(self, enabled: bool) -> None:
            try:
                btn = self.query_one("#run-button")
                if hasattr(btn, "disabled"):
                    btn.disabled = not enabled
            except Exception:
                pass

        # --- Clipboard utilities & copy actions
        def _copy_to_clipboard(self, text: str) -> bool:
            """Best-effort copy to system clipboard across Textual versions.

            Returns True if the framework reported success, False otherwise.
            """
            try:
                if hasattr(self, "copy_to_clipboard"):
                    self.copy_to_clipboard(text)
                    return True
            except Exception:
                pass
            for obj_name in ("set_clipboard",):
                try:
                    if hasattr(self, obj_name):
                        getattr(self, obj_name)(text)
                        return True
                except Exception:
                    pass
            try:
                scr = getattr(self, "screen", None)
                if scr is not None and hasattr(scr, "set_clipboard"):
                    scr.set_clipboard(text)
                    return True
            except Exception:
                pass
            try:
                drv = getattr(self, "driver", None)
                if drv is not None and hasattr(drv, "set_clipboard"):
                    drv.set_clipboard(text)
                    return True
            except Exception:
                pass
            return False

        def action_copy_status(self) -> None:
            """Copy the current status line text to clipboard."""
            try:
                status_widget = self.query_one("#run-status")
            except Exception:
                status_widget = None
            text = ""
            if status_widget is not None:
                try:
                    content = getattr(status_widget, "renderable", None)
                    if content is None:
                        content = getattr(status_widget, "text", None)
                    text = str(content) if content is not None else ""
                except Exception:
                    text = ""
            if not text:
                text = "Status: idle"
            ok = self._copy_to_clipboard(text)
            self._add_meta(
                "Status copied to clipboard" if ok else "Could not access clipboard"
            )

        def action_copy_last_error(self) -> None:
            """Copy the last error message to clipboard.

            Priority order:
            1) Last recorded error from error callbacks
            2) Last output line containing 'error'
            3) Entire status line if it mentions an error
            """
            err_text: str | None = None
            try:
                errs = getattr(self, "_errors", []) or []
                if errs:
                    err_text = str(errs[-1])
            except Exception:
                err_text = None
            if not err_text:
                try:
                    lines = list(getattr(self, "_output_lines", []) or [])
                except Exception:
                    lines = []
                for ln in reversed(lines):
                    try:
                        if "error" in ln.lower():
                            err_text = ln
                            break
                    except Exception as exc:
                        logging.debug(f"Scanning output line for error failed: {exc}")
                        continue
            if not err_text:
                try:
                    status_widget = self.query_one("#run-status")
                    content = getattr(status_widget, "renderable", None)
                    if content is None:
                        content = getattr(status_widget, "text", None)
                    status_text = str(content) if content is not None else ""
                    if "error" in status_text.lower():
                        err_text = status_text
                except Exception:
                    err_text = None
            if not err_text:
                self._add_meta("No error found to copy")
                return
            ok = self._copy_to_clipboard(err_text)
            self._add_meta(
                "Error copied to clipboard" if ok else "Could not access clipboard"
            )

        def _show_summary_panel(self) -> None:
            # Ensure bottom area is visible and unhide summary panel
            self._show_bottom_panel()
            try:
                panel = self.query_one("#summary-panel")
            except Exception:
                panel = None
            if panel is not None:
                try:
                    panel.remove_class("hidden")
                except Exception:
                    try:
                        styles = getattr(panel, "styles", None)
                        if styles and hasattr(styles, "display"):
                            styles.display = "block"
                    except Exception:
                        pass
            self._refresh_bottom_visibility()

        def _show_bottom_panel(self) -> None:
            try:
                container = self.query_one("#bottom")
            except Exception:
                return
            try:
                container.remove_class("hidden")
            except Exception:
                try:
                    styles = getattr(container, "styles", None)
                    if styles and hasattr(styles, "display"):
                        styles.display = "block"
                except Exception:
                    pass

        def _hide_bottom_panel(self) -> None:
            try:
                container = self.query_one("#bottom")
            except Exception:
                return
            try:
                container.add_class("hidden")
            except Exception:
                try:
                    styles = getattr(container, "styles", None)
                    if styles and hasattr(styles, "display"):
                        styles.display = "none"
                except Exception:
                    pass

        def _refresh_bottom_visibility(self) -> None:
            """Hide entire bottom area if no output and summary is hidden and status is idle."""
            try:
                summary_panel = self.query_one("#summary-panel")
                output_panel = self.query_one("#output-panel")
                status_widget = self.query_one("#run-status")
                bottom_container = self.query_one("#bottom")
            except Exception:
                return
            try:
                s_classes: set[str] = set(getattr(summary_panel, "classes", []) or [])
                o_classes: set[str] = set(getattr(output_panel, "classes", []) or [])
                is_summary_hidden = "hidden" in s_classes
                is_output_hidden = "hidden" in o_classes
            except Exception:
                is_summary_hidden = False
                is_output_hidden = False
            try:
                status_text = getattr(status_widget, "renderable", "") or getattr(
                    status_widget, "text", ""
                )
                status_str = (
                    str(status_text)
                    if not isinstance(status_text, str)
                    else status_text
                )
                # Show bottom if status has more than the plain idle marker
                has_status_info = status_str.strip() not in {"", "Status: idle"}
            except Exception:
                has_status_info = False
            if is_summary_hidden and is_output_hidden and not has_status_info:
                self._hide_bottom_panel()
            else:
                self._show_bottom_panel()
            # Expand bottom when any panel is visible; otherwise compact to auto height
            try:
                any_panel_visible = not (is_summary_hidden and is_output_hidden)
                if any_panel_visible:
                    bottom_container.add_class("expanded")
                else:
                    bottom_container.remove_class("expanded")
            except Exception:
                # Best-effort; ignore if styles not supported
                pass

        def _hide_summary_panel(self) -> None:
            try:
                panel = self.query_one("#summary-panel")
            except Exception:
                return
            try:
                panel.add_class("hidden")
            except Exception:
                try:
                    styles = getattr(panel, "styles", None)
                    if styles and hasattr(styles, "display"):
                        styles.display = "none"
                except Exception:
                    pass

        def action_focus_filter(self) -> None:
            """Focus the most relevant filter/input for the active pane."""
            target_input_id: str | None = None
            focus = None
            # Try to get currently focused widget
            for attr in ("focused",):
                try:
                    focus = getattr(self, attr, None) or getattr(
                        self.screen, attr, None
                    )
                except Exception as exc:
                    logging.debug(f"Focus attribute retrieval failed: {exc}")
                    continue
                if focus is not None:
                    break

            # Helper to check ancestry membership
            def within(container_id: str) -> bool:
                try:
                    container = self.query_one(f"#{container_id}")
                except Exception:
                    return False
                node = focus
                seen = 0
                while node is not None and seen < 100:
                    if node is container:
                        return True
                    try:
                        node = getattr(node, "parent", None)
                    except Exception as exc:
                        logging.debug(f"Focus ancestry traversal failed: {exc}")
                        node = None
                    seen += 1
                return False

            # Prefer bottom panels when focus is inside them
            try:
                if within("output-panel"):
                    target_input_id = "filter-output"
                elif within("summary-panel"):
                    target_input_id = "filter-summary"
            except Exception as exc:
                logging.debug(f"Bottom panel detection failed: {exc}")

            # If not bottom, detect active top tab via focus location
            if target_input_id is None:
                if within("tab-devices"):
                    target_input_id = "filter-devices"
                elif within("tab-groups"):
                    target_input_id = "filter-groups"
                elif within("tab-sequences"):
                    target_input_id = "filter-sequences"
                elif within("tab-commands"):
                    # Not a filter but sensible default
                    target_input_id = "input-commands"

            # If still unknown, look up active tabs by container state
            if target_input_id is None:
                # Check targets-tabs active
                try:
                    tabs = self.query_one("#targets-tabs")
                    active = getattr(tabs, "active", None)
                    active_id = getattr(active, "id", None) or str(active or "")
                    if "devices" in str(active_id):
                        target_input_id = "filter-devices"
                    elif "groups" in str(active_id):
                        target_input_id = "filter-groups"
                except Exception:
                    pass
            if target_input_id is None:
                try:
                    tabs = self.query_one("#actions-tabs")
                    active = getattr(tabs, "active", None)
                    active_id = getattr(active, "id", None) or str(active or "")
                    if "sequences" in str(active_id):
                        target_input_id = "filter-sequences"
                    elif "commands" in str(active_id):
                        target_input_id = "input-commands"
                except Exception:
                    pass

            # Final fallback: prefer output filter if panel visible, else summary, else devices
            if target_input_id is None:
                try:
                    out_panel = self.query_one("#output-panel")
                    out_hidden = "hidden" in (getattr(out_panel, "classes", []) or [])
                    if not out_hidden:
                        target_input_id = "filter-output"
                except Exception:
                    pass
            if target_input_id is None:
                try:
                    sum_panel = self.query_one("#summary-panel")
                    sum_hidden = "hidden" in (getattr(sum_panel, "classes", []) or [])
                    if not sum_hidden:
                        target_input_id = "filter-summary"
                except Exception:
                    pass
            if target_input_id is None:
                target_input_id = "filter-devices"

            self._focus_input_by_id(target_input_id)

        def _focus_input_by_id(self, element_id: str) -> None:
            try:
                w = self.query_one(f"#{element_id}")
            except Exception:
                return
            # Try widget's focus method first
            try:
                if hasattr(w, "focus"):
                    w.focus()
                    return
            except Exception:
                pass
            # Fallback to focusing via app
            try:
                if hasattr(self, "set_focus"):
                    self.set_focus(w)
            except Exception:
                pass

        def action_toggle_theme(self) -> None:
            """Toggle between light and dark theme, with compatibility fallbacks."""
            try:
                current_dark = bool(self.dark)
            except Exception:
                current_dark = getattr(self, "_dark_mode", True)
            new_dark = not current_dark
            self._dark_mode = new_dark
            self._apply_theme(new_dark)

        def _apply_theme(self, dark: bool) -> None:
            # Preferred: property 'dark' on App
            try:
                if hasattr(self, "dark"):
                    self.dark = dark
                    return
            except Exception as exc:
                logging.debug(f"Setting App.dark failed: {exc}")
            # Legacy: set_theme("dark"|"light")
            try:
                if hasattr(self, "set_theme"):
                    theme_name = "dark" if dark else "light"
                    self.set_theme(theme_name)
                    # Continue to refresh UI below
            except Exception as exc:
                logging.debug(f"set_theme failed: {exc}")
            # Fallback: use built-in action if available
            try:
                # If App has an action to toggle, ensure it matches desired state
                has_dark_attr = hasattr(self, "dark")
                current = bool(self.dark) if has_dark_attr else None
                if hasattr(self, "action_toggle_dark"):
                    if current is None or current != dark:
                        self.action_toggle_dark()
            except Exception as exc:
                logging.debug(f"action_toggle_dark failed: {exc}")
            # Refresh CSS/Screen to reflect theme changes
            for method in ("refresh_css", "reload_css"):
                try:
                    if hasattr(self, method):
                        getattr(self, method)()
                        break
                except Exception as exc:
                    logging.debug(f"{method} failed: {exc}")
            try:
                if hasattr(self, "refresh"):
                    self.refresh()
            except Exception:
                pass
            # Fallback: no-op; CSS uses theme vars so best effort only

    # Helpers are provided by network_toolkit.tui.helpers

    # Note: We rely on DeviceSession raising NetworkToolkitError for failures

    # Launch the app
    _App().run()
