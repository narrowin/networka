from __future__ import annotations

import logging
from typing import Any

from network_toolkit.tui.helpers import log_write


class OutputPanelManager:
    """Manages the Output panel: All log, per-device tabs, buffers, and filtering.

    This class encapsulates interaction with TabbedContent/TabPane across
    Textual versions and maintains in-memory buffers so the UI can be
    reconstructed at any time.
    """

    def __init__(self, app: Any, compat: Any) -> None:
        self.app = app
        self.compat = compat
        # Expose buffers/maps on the app for legacy access/tests
        if not hasattr(app, "_output_device_logs"):
            app._output_device_logs = {}
        if not hasattr(app, "_output_device_lines"):
            app._output_device_lines = {}
        if not hasattr(app, "_output_device_panes"):
            app._output_device_panes = {}
        if not hasattr(app, "_output_lines"):
            app._output_lines = []

    # ----- public API -----
    def reset(self) -> None:
        """Clear All output, remove dynamic device tabs, and reset buffers."""
        # Clear All
        try:
            out_all = self.app.query_one("#output-log")
            if hasattr(out_all, "clear"):
                out_all.clear()
        except Exception:
            pass
        try:
            self.app._output_lines = []
        except Exception:
            pass
        # Remove all device tabs (prefer removing actual TabPane objects)
        tabs = self._get_tabs()
        device_keys = list(getattr(self.app, "_output_device_panes", {}).keys())
        for dev_key in device_keys:
            pane = self.app._output_device_panes.get(dev_key)
            if pane is not None and tabs is not None:
                removed = False
                for method in ("remove_pane", "remove", "remove_tabs"):
                    try:
                        if hasattr(tabs, method):
                            if method == "remove_tabs":
                                getattr(tabs, method)([pane])
                            else:
                                getattr(tabs, method)(pane)
                            removed = True
                            break
                    except Exception as exc:
                        logging.debug(f"Removing pane via {method} failed: {exc}")
                if not removed:
                    # Try remove_tab by label and by id
                    tab_id = self._tab_id_for_device(dev_key)
                    for meth in ("remove_tab",):
                        try:
                            if hasattr(tabs, meth):
                                # Attempt with label
                                try:
                                    getattr(tabs, meth)(dev_key)
                                    removed = True
                                    break
                                except Exception:
                                    # Attempt with id
                                    getattr(tabs, meth)(tab_id)
                                    removed = True
                                    break
                        except Exception as exc:
                            logging.debug(f"Removing tab via {meth} failed: {exc}")
                if not removed:
                    # Fallback: remove content child if we can reach it
                    try:
                        content = self.app.query_one(
                            f"#{self._tab_id_for_device(dev_key)}"
                        )
                    except Exception:
                        content = None
                    if content is not None:
                        self._remove_child(tabs, content)
                    else:
                        self._remove_child(tabs, pane)
        # Fallback sweep
        if tabs is not None:
            try:
                children = list(getattr(tabs, "children", []) or [])
            except Exception:
                children = []
            for child in children:
                try:
                    cid = getattr(child, "id", "") or ""
                except Exception:
                    cid = ""
                if cid.startswith("output-tab-") and cid != "output-tab-all":
                    self._remove_child(tabs, child)
            # Reset maps
            self.app._output_device_logs = {}
            self.app._output_device_lines = {}
            self.app._output_device_panes = {}
            # Activate All
            try:
                if tabs is not None and hasattr(tabs, "active"):
                    tabs.active = "output-tab-all"
            except Exception:
                pass

    def ensure_device_tab(self, device: str) -> Any | None:
        dev_key = str(device)
        if dev_key in self.app._output_device_logs:
            return self.app._output_device_logs[dev_key]
        tabs = self._get_tabs()
        if tabs is None:
            return None
        tab_id = self._tab_id_for_device(dev_key)
        # Create content log (id must match pane id for ContentSwitcher)
        try:
            log = self.compat.TextLogClass(id=tab_id, classes="scroll")
        except Exception:
            log = None
        if log is None:
            return None
        # Create pane and mount content
        pane = None
        try:
            pane = self.compat.TabPane(dev_key, log, id=tab_id)
        except Exception:
            try:
                pane = self.compat.TabPane(dev_key, id=tab_id)
            except Exception:
                pane = None
            if pane is not None and hasattr(pane, "mount"):
                try:
                    pane.mount(log)
                except Exception:
                    pass
        if pane is None:
            return None
        # Add it
        added = False
        for method in ("add_pane", "add", "add_panes"):
            try:
                if hasattr(tabs, method):
                    if method == "add_panes":
                        getattr(tabs, method)([pane])
                    else:
                        getattr(tabs, method)(pane)
                    added = True
                    break
            except Exception as exc:
                logging.debug(f"Adding tab pane via {method} failed: {exc}")
        if not added and hasattr(tabs, "add_tab"):
            try:
                tabs.add_tab(dev_key, log, id=tab_id)
                added = True
            except Exception as exc:
                logging.debug(f"Adding tab via add_tab failed: {exc}")
        if not added:
            return None
        self.app._output_device_logs[dev_key] = log
        self.app._output_device_panes[dev_key] = pane
        self.app._output_device_lines.setdefault(dev_key, [])
        return log

    def append_all(self, text: str) -> None:
        lines = self._split_lines(text)
        if not lines:
            return
        try:
            self.app._maybe_show_output_panel()
        except Exception:
            pass
        try:
            self.app._output_lines.extend(lines)
        except Exception:
            self.app._output_lines = list(lines)
        # Render depending on filter
        try:
            out_log = self.app.query_one("#output-log")
        except Exception:
            out_log = None
        if out_log is None:
            return
        filt = (getattr(self.app, "_output_filter", "") or "").strip().lower()
        if filt:
            self._render_filtered(out_log, self.app._output_lines, filt)
        else:
            for line in lines:
                log_write(out_log, line)

    def append_device(self, device: str, text: str) -> None:
        lines = self._split_lines(text)
        if not lines:
            return
        try:
            self.app._maybe_show_output_panel()
        except Exception:
            pass
        dev_key = str(device)
        try:
            self.app._output_lines.extend(lines)
        except Exception:
            self.app._output_lines = list(lines)
        buf = self.app._output_device_lines.setdefault(dev_key, [])
        buf.extend(lines)
        log_dev = self.ensure_device_tab(dev_key)
        filt = (getattr(self.app, "_output_filter", "") or "").strip().lower()
        if filt:
            try:
                self.apply_filter(filt)
            except Exception:
                pass
            return
        # Append to All and device logs
        try:
            out_all = self.app.query_one("#output-log")
            for line in lines:
                log_write(out_all, line)
        except Exception:
            pass
        try:
            if log_dev is not None:
                for line in lines:
                    log_write(log_dev, line)
        except Exception:
            pass

    def apply_filter(self, value: str) -> None:
        self.app._output_filter = value
        filt = (value or "").strip().lower()
        # Determine active tab
        try:
            tabs = self._get_tabs()
            active = getattr(tabs, "active", None)
            active_id = getattr(active, "id", None) or str(active or "")
        except Exception:
            active_id = None
        log_widget: Any | None = None
        lines_src: list[str] = []
        try:
            if not active_id or "output-tab-all" in str(active_id):
                log_widget = self.app.query_one("#output-log")
                lines_src = list(self.app._output_lines)
            elif str(active_id).startswith("output-tab-"):
                dev_part = str(active_id)[len("output-tab-") :]
                dev_key = self._find_device_key(dev_part)
                log_widget = self.app._output_device_logs.get(dev_key)
                lines_src = list(self.app._output_device_lines.get(dev_key, []))
        except Exception:
            pass
        if log_widget is None:
            return
        self._render_filtered(log_widget, lines_src, filt)

    def recreate(self) -> None:
        """Recreate tabs and logs from in-memory buffers."""
        tabs = self._get_tabs()
        if tabs is None:
            return
        # Clear and re-add per-device tabs
        self.reset()
        for dev_key in list(self.app._output_device_lines.keys()):
            log = self.ensure_device_tab(dev_key)
            if log is None:
                continue
            for line in self.app._output_device_lines.get(dev_key, []):
                log_write(log, line)
        # Re-render All
        try:
            out_all = self.app.query_one("#output-log")
            filt = (getattr(self.app, "_output_filter", "") or "").strip().lower()
            if filt:
                self._render_filtered(out_all, self.app._output_lines, filt)
            else:
                if hasattr(out_all, "clear"):
                    out_all.clear()
                for line in self.app._output_lines:
                    log_write(out_all, line)
        except Exception:
            pass

    # ----- helpers -----
    def _get_tabs(self) -> Any | None:
        try:
            return self.app.query_one("#output-tabs")
        except Exception:
            return None

    def _tab_id_for_device(self, device_key: str) -> str:
        dev_id = self._sanitize_id(device_key)
        return f"output-tab-{dev_id}"

    def _split_lines(self, text: str) -> list[str]:
        try:
            s = str(text)
        except Exception:
            s = f"{text}"
        return list(s.splitlines())

    def _render_filtered(self, log_widget: Any, lines: list[str], filt: str) -> None:
        try:
            if hasattr(log_widget, "clear"):
                log_widget.clear()
        except Exception:
            pass
        for line in lines:
            try:
                if not filt or (filt in line.lower()):
                    log_write(log_widget, line)
            except Exception:
                pass

    def _find_device_key(self, dev_id_part: str) -> str:
        # Match sanitized id first
        for k in self.app._output_device_lines.keys():
            if self._sanitize_id(k) == dev_id_part:
                return str(k)
        return str(dev_id_part)

    def _sanitize_id(self, name: str) -> str:
        # Prefer app helper if present
        try:
            return str(self.app._sanitize_id(name))
        except Exception:
            try:
                import re

                return re.sub(r"[^A-Za-z0-9_.-]", "-", name)
            except Exception:
                return name.replace(" ", "-")

    def _remove_tab_by_id(self, tabs: Any | None, pane_id: str) -> None:
        if tabs is None:
            return
        pane = None
        try:
            pane = self.app.query_one(f"#{pane_id}")
        except Exception:
            pane = None
        if pane is None:
            return
        for method in ("remove_pane", "remove", "remove_tabs"):
            try:
                if hasattr(tabs, method):
                    if method == "remove_tabs":
                        getattr(tabs, method)([pane])
                    else:
                        getattr(tabs, method)(pane)
                    return
            except Exception as exc:
                logging.debug(f"Removing device tab via {method} failed: {exc}")
        # Fallback remove on child
        self._remove_child(tabs, pane)

    def _remove_child(self, tabs: Any, child: Any) -> None:
        try:
            if hasattr(tabs, "remove"):
                tabs.remove(child)
            elif hasattr(child, "remove"):
                child.remove()
            elif hasattr(child, "unmount"):
                child.unmount()
        except Exception:
            pass
