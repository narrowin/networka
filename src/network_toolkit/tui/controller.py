"""Controller for the Textual TUI.

Encapsulates event handling and run lifecycle logic. Keeps UI plumbing
methods in the App class while coordinating behavior here for clarity.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from network_toolkit.tui.constants import STARTUP_NOTICE
from network_toolkit.tui.models import CancellationToken


class TuiController:
    def __init__(
        self, app: Any, compat: Any, data: Any, service: Any, state: Any
    ) -> None:
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
        # Startup notice: use toast notification (lower-right, orange frame)
        try:
            self.compat.notify(app, STARTUP_NOTICE, timeout=3, severity="warning")
        except Exception:
            # If notify isn't available, skip (avoid status-line fallback)
            pass
        # Record UI thread identity for safe callback dispatching
        try:
            app._ui_thread_ident = threading.get_ident()
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
        # Async task + cancellation token for active run
        app._run_task = None
        app._cancel_token = None
        # Background tasks and toast-prompt state flags
        app._bg_tasks = set()
        app._cancel_prompt_active = False
        app._cancel_mode_prompt_active = False
        app._quit_prompt_active = False

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
                lines: list[str] = [
                    str(x) for x in (getattr(app, "_output_lines", []) or [])
                ]
                for line in lines:
                    if not filt or (filt in line.lower()):
                        from network_toolkit.tui.helpers import log_write

                        log_write(out_log, line)

    async def action_confirm(self) -> None:
        app = self.app
        service = self.service
        state = self.state
        # Disallow starting a new run if one is active: show toast and let on_key handle
        if getattr(app, "_run_active", False):
            app._cancel_prompt_active = True
            app._add_meta(
                "Run already in progress — press 'y' to cancel, 'n' or Enter to continue."
            )
            try:
                self.compat.notify(
                    app,
                    "A job is already running. Cancel it? [y/N]",
                    timeout=5,
                    severity="warning",
                )
            except Exception:
                pass
            return

        # Prepare UI for a new run
        out_log = app.query_one("#output-log")
        if hasattr(out_log, "clear"):
            out_log.clear()
        try:
            app._output_lines = []
        except Exception:
            pass
        app._errors = []
        app._meta = []
        try:
            app.query_one("#run-summary").update("")
            app._hide_summary_panel()
            app._hide_output_panel()
        except Exception:
            pass
        app._add_meta("Starting run...")
        app._run_active = True
        app._cancel_token = CancellationToken()
        app._set_inputs_enabled(False)
        app._set_run_enabled(False)

        async def _runner() -> None:
            start_ts: float | None = None
            try:
                logging.disable(logging.CRITICAL)
                start_ts = time.monotonic()
                app._collect_state()
                devices = await asyncio.to_thread(
                    service.resolve_devices, state.devices, state.groups
                )
                if not devices:
                    app._dispatch_ui(app._render_summary, "No devices selected.")
                    try:
                        msg = "Status: idle — No devices selected."
                        app.query_one("#run-status").update(msg)
                        app._refresh_bottom_visibility()
                    except Exception:
                        pass
                    return
                plan = service.build_plan(devices, state.sequences, state.command_text)
                if not plan:
                    app._dispatch_ui(
                        app._render_summary, "No sequences or commands provided."
                    )
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
                    app.query_one("#run-status").update(
                        f"Status: running 0/{total} (press Ctrl+C to cancel)"
                    )
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
                    cancel=app._cancel_token,
                )
                try:
                    if getattr(app, "_output_lines", None):
                        app._show_output_panel()
                        try:
                            out_log = app.query_one("#output-log")
                            if hasattr(out_log, "clear"):
                                out_log.clear()
                            filt = (
                                (getattr(app, "_output_filter", "") or "")
                                .strip()
                                .lower()
                            )
                            lines: list[str] = [
                                str(x)
                                for x in (getattr(app, "_output_lines", []) or [])
                            ]
                            for line in lines:
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
                app._dispatch_ui(
                    app._render_summary, f"Run failed: {e} (after {elapsed:.2f}s)"
                )
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
                    app._cancel_token = None
                    app._run_task = None
                    # No prompt state flags
                    # After run completes, clear any selections in the UI
                    try:
                        app._dispatch_ui(app._clear_all_selections)
                    except Exception:
                        pass
                except Exception:
                    pass

        # Schedule runner without blocking UI loop
        try:
            loop = asyncio.get_running_loop()
            app._run_task = loop.create_task(_runner())
        except Exception:
            # Fallback: run inline (still async) if loop is not accessible
            await _runner()

    async def action_cancel(self) -> None:
        app = self.app
        # Trigger cooperative cancellation and update UI; do nothing if idle
        try:
            token = getattr(app, "_cancel_token", None)
            if token is not None:
                token.set()
                app._add_meta("Cancellation requested")
                try:
                    status = app.query_one("#run-status")
                    status.update("Status: cancelling…")
                except Exception:
                    pass
                # No prompt state flags
        except Exception:
            pass

    async def action_cancel_hard(self) -> None:
        """Hard cancel: set token and aggressively disconnect active sessions."""
        app = self.app
        try:
            token = getattr(app, "_cancel_token", None)
            if token is not None:
                try:
                    token.set()
                except Exception:
                    pass
                try:
                    # Ask the service to close active sessions to interrupt blocking calls
                    self.service.request_hard_cancel(token)
                except Exception:
                    pass
                app._add_meta(
                    "Hard cancellation requested — connections will be terminated."
                )
                try:
                    status = app.query_one("#run-status")
                    status.update(
                        "Status: cancelling (hard) — connections will be terminated; in-flight operations may be partially applied"
                    )
                except Exception:
                    pass
                # No prompt state flags
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
        # Handle toast-driven prompts first (cancel/quit flows)
        try:
            if getattr(app, "_cancel_prompt_active", False):
                if key in {"y"}:
                    app._cancel_prompt_active = False
                    app._cancel_mode_prompt_active = True
                    try:
                        self.compat.notify(
                            app,
                            "Cancel type? Soft [s] (recommended) or Hard [h]. Hard will close sessions immediately and may leave devices in a partial state.",
                            timeout=8,
                            severity="warning",
                        )
                    except Exception:
                        pass
                    if hasattr(event, "stop"):
                        event.stop()
                    return
                if key in {"n", "enter", "return", "escape"}:
                    app._cancel_prompt_active = False
                    try:
                        status = app.query_one("#run-status")
                        status.update("Status: running — Continuing current run")
                        app._refresh_bottom_visibility()
                    except Exception:
                        try:
                            self.compat.notify(
                                app,
                                "Continuing current run",
                                timeout=2,
                                severity="info",
                            )
                        except Exception:
                            pass
                    if hasattr(event, "stop"):
                        event.stop()
                    return
            if getattr(app, "_cancel_mode_prompt_active", False):
                if key in {"s", "enter", "return"}:  # default soft
                    app._cancel_mode_prompt_active = False
                    try:
                        task = asyncio.create_task(self.action_cancel())
                        self.app._bg_tasks.add(task)
                        task.add_done_callback(self.app._bg_tasks.discard)
                    except Exception:
                        pass
                    if hasattr(event, "stop"):
                        event.stop()
                    return
                if key == "h":
                    app._cancel_mode_prompt_active = False
                    try:
                        task = asyncio.create_task(self.action_cancel_hard())
                        self.app._bg_tasks.add(task)
                        task.add_done_callback(self.app._bg_tasks.discard)
                    except Exception:
                        pass
                    if hasattr(event, "stop"):
                        event.stop()
                    return
                if key in {"n", "escape"}:
                    app._cancel_mode_prompt_active = False
                    try:
                        status = app.query_one("#run-status")
                        status.update("Status: running — Continuing current run")
                        app._refresh_bottom_visibility()
                    except Exception:
                        try:
                            self.compat.notify(
                                app,
                                "Continuing current run",
                                timeout=2,
                                severity="info",
                            )
                        except Exception:
                            pass
                    if hasattr(event, "stop"):
                        event.stop()
                    return
            if getattr(app, "_quit_prompt_active", False):
                if key == "y":
                    app._quit_prompt_active = False
                    try:
                        if hasattr(app, "exit"):
                            app.exit()
                        else:
                            raise SystemExit(0)
                    except Exception:
                        raise SystemExit(0) from None
                if key in {"n", "enter", "return", "escape"}:
                    app._quit_prompt_active = False
                    if hasattr(event, "stop"):
                        event.stop()
                    return
        except Exception:
            pass
        if key == "q":
            # If any overlay is visible, close it; otherwise ask to quit
            try:
                sum_panel = app.query_one("#summary-panel")
                help_panel = app.query_one("#help-panel")
                out_panel = app.query_one("#output-panel")
                s_hidden = "hidden" in (getattr(sum_panel, "classes", []) or [])
                h_hidden = "hidden" in (getattr(help_panel, "classes", []) or [])
                o_hidden = "hidden" in (getattr(out_panel, "classes", []) or [])
                any_visible = not (s_hidden and h_hidden and o_hidden)
            except Exception:
                any_visible = False
            if any_visible:
                try:
                    app.action_close_overlays()
                except Exception:
                    pass
                try:
                    if hasattr(event, "stop"):
                        event.stop()
                except Exception:
                    pass
                return

            # No overlays: ask to quit via toast and let on_key handle y/N
            app._quit_prompt_active = True
            try:
                self.compat.notify(
                    app, "Do you want to quit? [y/N]", timeout=5, severity="warning"
                )
            except Exception:
                pass
            try:
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
            return
        if key == "escape":
            try:
                app.action_close_overlays()
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
        elif key in {"ctrl+q"}:
            # Disable Ctrl+Q quitting entirely
            try:
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
        elif key == "s":
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
        elif key == "h":
            try:
                app.action_toggle_help()
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
        elif key in {"ctrl+c"}:
            # Ctrl+C: show cancel y/N toast; on_key will handle response and next step
            try:
                if getattr(app, "_run_active", False):
                    app._cancel_prompt_active = True
                    try:
                        self.compat.notify(
                            app,
                            "A job is already running. Cancel it? [y/N]",
                            timeout=5,
                            severity="warning",
                        )
                    except Exception:
                        pass
                if hasattr(event, "stop"):
                    event.stop()
            except Exception:
                pass
