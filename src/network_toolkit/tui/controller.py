"""Controller for the Textual TUI.

Encapsulates event handling and run lifecycle logic. Keeps UI plumbing
methods in the App class while coordinating behavior here for clarity.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from network_toolkit.tui.constants import STARTUP_NOTICE


class TuiController:
    def __init__(self, app: Any, compat: Any, data: Any, service: Any, state: Any) -> None:
        self.app = app
        self.compat = compat
        self.data = data
        self.service = service
        self.state = state

    async def on_mount(self) -> None:
        app = self.app
        data = self.data
        try:
            t = data.targets()
            a = data.actions()
            # Keep base lists for filtering
            app._all_devices = list(t.devices)
            app._all_groups = list(t.groups)
            app._all_sequences = list(a.sequences)
            app._populate_selection_list("list-devices", app._all_devices)
            app._populate_selection_list("list-groups", app._all_groups)
            app._populate_selection_list("list-sequences", app._all_sequences)
        except Exception:
            pass
        # Startup notice
        try:
            try:
                self.compat.notify(app, STARTUP_NOTICE, timeout=3, severity="warning")
            except AttributeError:
                try:
                    status = app.query_one("#run-status")
                    try:
                        prev_text = (
                            getattr(getattr(status, "renderable", None), "plain", None)
                            or "Status: idle"
                        )
                    except Exception:
                        prev_text = "Status: idle"
                    try:
                        status.update(STARTUP_NOTICE)
                    except Exception:
                        pass
                    try:
                        app.set_timer(3.0, lambda: status.update(prev_text))
                    except Exception:
                        async def _restore() -> None:
                            try:
                                await asyncio.sleep(3)
                                status.update(prev_text)
                            except Exception:
                                pass
                        try:
                            app.call_later(_restore)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        # Record UI thread identity for safe callback dispatching
        try:
            app._ui_thread_ident = threading.get_ident()  # type: ignore[name-defined]
        except Exception:
            app._ui_thread_ident = -1
        # Toggling states
        app._summary_user_hidden = False
        app._output_user_hidden = False
        app._run_active = False
        try:
            app._dark_mode = bool(getattr(app, "dark", True))
        except Exception:
            app._dark_mode = True
        app._summary_filter = ""
        app._output_filter = ""
        app._output_lines = []
        app._refresh_bottom_visibility()

    async def on_input_changed(self, event: Any) -> None:
        app = self.app
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
        if sender_id == "filter-devices":
            base: list[str] = list(getattr(app, "_all_devices", []) or [])
            try:
                sel_widget = app.query_one("#list-devices")
                current_sel: set[str] = app._selected_values(sel_widget)
            except Exception:
                current_sel = set()
            items = [d for d in base if text in d.lower()]
            app._populate_selection_list("list-devices", items, selected=current_sel)
            return
        if sender_id == "filter-groups":
            base = list(getattr(app, "_all_groups", []) or [])
            try:
                sel_widget = app.query_one("#list-groups")
                current_sel = app._selected_values(sel_widget)
            except Exception:
                current_sel = set()
            items = [g for g in base if text in g.lower()]
            app._populate_selection_list("list-groups", items, selected=current_sel)
            return
        if sender_id == "filter-sequences":
            base = list(getattr(app, "_all_sequences", []) or [])
            try:
                sel_widget = app.query_one("#list-sequences")
                current_sel = app._selected_values(sel_widget)
            except Exception:
                current_sel = set()
            items = [s for s in base if text in s.lower()]
            app._populate_selection_list("list-sequences", items, selected=current_sel)
            return
        if sender_id == "filter-summary":
            app._summary_filter = value
            app._render_summary()
            return
        if sender_id == "filter-output":
            app._output_filter = value
            try:
                out_log = app.query_one("#output-log")
            except Exception:
                out_log = None
            if out_log is not None:
                try:
                    if hasattr(out_log, "clear"):
                        out_log.clear()
                except Exception:
                    pass
                filt = (value or "").strip().lower()
                for line in getattr(app, "_output_lines", []) or []:
                    if not filt or (filt in line.lower()):
                        from network_toolkit.tui.helpers import log_write

                        log_write(out_log, line)

    async def action_confirm(self) -> None:
        app = self.app
        service = self.service
        state = self.state
        out_log = app.query_one("#output-log")
        if hasattr(out_log, "clear"):
            out_log.clear()
        try:
            app._output_lines = []
        except Exception:
            pass
        app._errors = []
        app._meta = []
        start_ts: float | None = None
        try:
            app.query_one("#run-summary").update("")
            app._hide_summary_panel()
            app._hide_output_panel()
        except Exception:
            pass
        app._add_meta("Starting run...")
        logging.disable(logging.CRITICAL)
        try:
            app._run_active = True
            app._set_inputs_enabled(False)
            app._set_run_enabled(False)
            start_ts = time.monotonic()
            app._collect_state()
            devices = await asyncio.to_thread(
                service.resolve_devices, state.devices, state.groups
            )
            if not devices:
                app._render_summary("No devices selected.")
                try:
                    msg = "Status: idle — No devices selected."
                    app.query_one("#run-status").update(msg)
                    app._refresh_bottom_visibility()
                except Exception:
                    pass
                return
            plan = service.build_plan(devices, state.sequences, state.command_text)
            if not plan:
                app._render_summary("No sequences or commands provided.")
                try:
                    msg = "Status: idle — No sequences or commands provided."
                    app.query_one("#run-status").update(msg)
                    app._refresh_bottom_visibility()
                except Exception:
                    pass
                return
            total = len(plan)
            try:
                app._show_bottom_panel()
                app.query_one("#run-status").update(f"Status: running 0/{total}")
            except Exception:
                pass
            from network_toolkit.tui.models import RunCallbacks

            summary_result = await service.run_plan(
                plan,
                RunCallbacks(
                    on_output=lambda m: app._dispatch_ui(app._output_append, m),
                    on_error=lambda m: app._dispatch_ui(app._add_error, m),
                    on_meta=lambda m: app._dispatch_ui(app._add_meta, m),
                ),
            )
            try:
                if getattr(app, "_output_lines", None):
                    app._show_output_panel()
                    try:
                        out_log = app.query_one("#output-log")
                        if hasattr(out_log, "clear"):
                            out_log.clear()
                        filt = (
                            (getattr(app, "_output_filter", "") or "").strip().lower()
                        )
                        for line in app._output_lines:
                            if not filt or (filt in line.lower()):
                                from network_toolkit.tui.helpers import log_write

                                log_write(out_log, line)
                    except Exception:
                        pass
                elapsed = time.monotonic() - start_ts
                summary_with_time = (
                    f"{summary_result.human_summary()} (duration: {elapsed:.2f}s)"
                )
                app._render_summary(summary_with_time)
                try:
                    err_count = len(getattr(app, "_errors", []) or [])
                except Exception:
                    err_count = 0
                status_msg = f"Status: idle — {summary_with_time}"
                if err_count:
                    status_msg += " — errors available (press s)"
                app.query_one("#run-status").update(status_msg)
                app._refresh_bottom_visibility()
            except Exception:
                pass
        except Exception as e:  # noqa: BLE001
            try:
                elapsed = (
                    (time.monotonic() - start_ts) if (start_ts is not None) else 0.0
                )
            except Exception:
                elapsed = 0.0
            app._render_summary(f"Run failed: {e} (after {elapsed:.2f}s)")
            try:
                app.query_one("#run-status").update(
                    f"Status: idle — Run failed: {e}"
                )
                if getattr(app, "_output_lines", None):
                    app._show_output_panel()
                app._refresh_bottom_visibility()
            except Exception:
                pass
        finally:
            logging.disable(logging.NOTSET)
            try:
                app._run_active = False
                app._set_inputs_enabled(True)
                app._set_run_enabled(True)
            except Exception:
                pass

    async def on_input_submitted(self, event: Any) -> None:
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

    def on_key(self, event: Any) -> None:
        app = self.app
        try:
            key = str(getattr(event, "key", "")).lower()
        except Exception:
            key = ""
        if key == "s":
            try:
                app.action_toggle_summary()
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
        elif key == "o":
            try:
                app.action_toggle_output()
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
        elif key == "t":
            try:
                app.action_toggle_theme()
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
        elif key == "f":
            try:
                app.action_focus_filter()
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
        elif key == "y":
            try:
                app.action_copy_last_error()
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
