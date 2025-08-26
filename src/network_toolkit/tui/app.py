"""Textual app for selecting targets and actions.

First iteration focuses on selection only:

Execution is not wired yet; we only collect selections and show a preview.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ClassVar

from network_toolkit.tui.clipboard import copy_to_clipboard
from network_toolkit.tui.compat import TextualNotInstalledError, load_textual
from network_toolkit.tui.constants import CSS as APP_CSS
from network_toolkit.tui.controller import TuiController
from network_toolkit.tui.data import TuiData
from network_toolkit.tui.helpers import log_write
from network_toolkit.tui.keymap import KEYMAP
from network_toolkit.tui.layout import compose_root
from network_toolkit.tui.models import SelectionState
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
    try:
        compat = load_textual()
        app_cls: Any = compat.App
    except TextualNotInstalledError as exc:  # pragma: no cover
        raise RuntimeError(str(exc)) from exc

    data = TuiData(config)

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
        _output_lines: list[str]
        _summary_filter: str
        _output_filter: str
        _summary_user_hidden: bool
        _output_user_hidden: bool
        _run_active: bool
        _dark_mode: bool
        _ui_thread_ident: int
        _controller: TuiController

        CSS = APP_CSS
        BINDINGS: ClassVar[list[Any]] = [
            compat.mk_binding(
                k.key,
                k.action,
                k.description,
                show=k.show,
                key_display=k.key_display,
                priority=k.priority,
            )
            for k in KEYMAP
        ]

        def compose(self) -> Any:
            # Delegate UI tree building to the layout module
            yield from compose_root(compat)

        async def on_mount(self) -> None:  # Populate lists after UI mounts
            # Create controller on mount to avoid overriding __init__ on dynamic base
            self._controller = TuiController(self, compat, data, service, state)
            await self._controller.on_mount()

        async def on_input_changed(self, event: Any) -> None:  # Textual Input change
            await self._controller.on_input_changed(event)

        async def action_confirm(self) -> None:
            await self._controller.action_confirm()

        async def on_input_submitted(self, event: Any) -> None:  # Textual Input submit
            await self._controller.on_input_submitted(event)

        async def on_button_pressed(self, event: Any) -> None:
            await self._controller.on_button_pressed(event)

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
            self._controller.on_key(event)

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
            return copy_to_clipboard(self, text)

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

        def _show_help_panel(self) -> None:
            try:
                panel = self.query_one("#help-panel")
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

        def _hide_help_panel(self) -> None:
            try:
                panel = self.query_one("#help-panel")
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
                help_panel = self.query_one("#help-panel")
                output_panel = self.query_one("#output-panel")
                status_widget = self.query_one("#run-status")
                bottom_container = self.query_one("#bottom")
            except Exception:
                return
            try:
                s_classes: set[str] = set(getattr(summary_panel, "classes", []) or [])
                h_classes: set[str] = set(getattr(help_panel, "classes", []) or [])
                o_classes: set[str] = set(getattr(output_panel, "classes", []) or [])
                is_summary_hidden = "hidden" in s_classes
                is_help_hidden = "hidden" in h_classes
                is_output_hidden = "hidden" in o_classes
            except Exception:
                is_summary_hidden = False
                is_help_hidden = False
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
            if (
                is_summary_hidden
                and is_help_hidden
                and is_output_hidden
                and not has_status_info
            ):
                self._hide_bottom_panel()
            else:
                self._show_bottom_panel()
            # Expand bottom when any panel is visible; otherwise compact to auto height
            try:
                any_panel_visible = not (
                    is_summary_hidden and is_help_hidden and is_output_hidden
                )
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

        def action_show_help(self) -> None:
            """Display a streamlined help view in the Help panel."""
            # Build content for help
            try:
                from rich.text import Text

                rich_text: Any = Text()
                rich_text.append("Help", style="bold")
                rich_text.append("\nPress Esc to close this help.")
                rich_text.append("\n\nKeys and actions:")
                for kb in KEYMAP:
                    key_label = kb.key_display or kb.key
                    rich_text.append("\n • ")
                    rich_text.append(f"{key_label} — ")
                    rich_text.append(kb.description)
                content: Any = rich_text
            except Exception:
                lines = [
                    "Help",
                    "Press Esc to close this help.",
                    "",
                    "Keys and actions:",
                ]
                for kb in KEYMAP:
                    key_label = kb.key_display or kb.key
                    lines.append(f" • {key_label} — {kb.description}")
                content = "\n".join(lines)

            # Update help widget
            try:
                help_log = self.query_one("#help-log")
                if hasattr(help_log, "clear"):
                    try:
                        help_log.clear()
                    except Exception:
                        pass
                if hasattr(help_log, "update"):
                    help_log.update(content)
                elif hasattr(help_log, "write"):
                    text = str(content)
                    for line in text.splitlines():
                        help_log.write(line)
            except Exception:
                pass

            # Show help panel, hide summary to avoid confusion
            try:
                self._hide_summary_panel()
            except Exception:
                pass
            try:
                self._show_help_panel()
            except Exception:
                pass
            try:
                status_msg = (
                    "Status: idle — Help (press h to refresh, s/o to toggle panels)"
                )
                self.query_one("#run-status").update(status_msg)
                self._refresh_bottom_visibility()
            except Exception:
                pass

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

        def action_toggle_help(self) -> None:
            """Toggle the visibility of the Help panel.

            If the Help panel is hidden, render and show it; if visible, hide it.
            """
            try:
                panel = self.query_one("#help-panel")
                classes: set[str] = set(getattr(panel, "classes", []) or [])
                is_hidden = "hidden" in classes
            except Exception:
                is_hidden = True
            if is_hidden:
                self.action_show_help()
            else:
                self._hide_help_panel()
                try:
                    self.query_one("#run-status").update("Status: idle")
                    self._refresh_bottom_visibility()
                except Exception:
                    pass

        def action_close_overlays(self) -> None:
            """Close any open bottom overlays (Help, Summary, Output)."""
            try:
                self._hide_help_panel()
            except Exception:
                pass
            try:
                self._hide_summary_panel()
            except Exception:
                pass
            try:
                self._hide_output_panel()
            except Exception:
                pass
            try:
                self.query_one("#run-status").update("Status: idle")
                self._refresh_bottom_visibility()
            except Exception:
                pass
            # Fallback: no-op; CSS uses theme vars so best effort only

    # Helpers are provided by network_toolkit.tui.helpers

    # Note: We rely on DeviceSession raising NetworkToolkitError for failures

    # Launch the app
    _App().run()
