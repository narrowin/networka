"""Compatibility helpers for Textual.

Lazily import Textual and normalize small API differences across versions.
Keep this module free of heavy imports at module import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class TextualNotInstalledError(RuntimeError):
    """Raised when the optional 'textual' dependency is missing."""


@dataclass(slots=True)
class TextualCompat:
    App: Any
    Binding: Any
    Horizontal: Any
    Vertical: Any
    Footer: Any
    Header: Any
    Input: Any
    Static: Any
    TabbedContent: Any
    TabPane: Any
    SelectionList: Any
    Button: Any
    TextLogClass: Any

    def mk_binding(
        self,
        key: str,
        action: str,
        desc: str,
        *,
        show: bool = False,
        key_display: str | None = None,
        priority: bool = False,
    ) -> Any:
        """Create a Binding instance compatible with multiple Textual versions."""
        cls = self.Binding
        try:
            return cls(key, action, desc, show, key_display, priority)
        except TypeError:
            try:
                return cls(key, action, desc, show)
            except TypeError:
                return cls(key, action)

    def notify(
        self, app: Any, message: str, *, timeout: float = 3, severity: str = "warning"
    ) -> None:
        """Show a temporary toast/notification if supported by this Textual version.

        Falls back to calling ``notify`` without severity when necessary.
        Raises AttributeError if notify is not available at all.
        """
        # Escape Rich markup so messages like "[s]" show literally across versions
        msg = str(message)
        try:  # optional rich
            from rich.markup import escape as _escape  # type: ignore

            msg = _escape(msg)
        except Exception:  # pragma: no cover - rich optional
            pass
        try:
            app.notify(msg, timeout=timeout, severity=severity)
        except TypeError:
            app.notify(msg, timeout=timeout)


def load_textual() -> TextualCompat:
    """Import Textual at runtime and return a compact compatibility wrapper.

    Raises TextualNotInstalledError if Textual cannot be imported.
    """
    try:  # pragma: no cover - UI framework import
        import importlib

        textual_app = importlib.import_module("textual.app")
        textual_binding = importlib.import_module("textual.binding")
        textual_containers = importlib.import_module("textual.containers")
        textual_widgets = importlib.import_module("textual.widgets")

        # Prefer RichLog; fall back to Log if not available in this Textual version
        try:
            text_log_cls: Any = getattr(textual_widgets, "RichLog")  # noqa: B009
        except AttributeError:
            text_log_cls = getattr(textual_widgets, "Log")  # noqa: B009

        return TextualCompat(
            App=getattr(textual_app, "App"),  # noqa: B009
            Binding=getattr(textual_binding, "Binding"),  # noqa: B009
            Horizontal=getattr(textual_containers, "Horizontal"),  # noqa: B009
            Vertical=getattr(textual_containers, "Vertical"),  # noqa: B009
            Footer=getattr(textual_widgets, "Footer"),  # noqa: B009
            Header=getattr(textual_widgets, "Header"),  # noqa: B009
            Input=getattr(textual_widgets, "Input"),  # noqa: B009
            Static=getattr(textual_widgets, "Static"),  # noqa: B009
            TabbedContent=getattr(textual_widgets, "TabbedContent"),  # noqa: B009
            TabPane=getattr(textual_widgets, "TabPane"),  # noqa: B009
            SelectionList=getattr(textual_widgets, "SelectionList"),  # noqa: B009
            Button=getattr(textual_widgets, "Button"),  # noqa: B009
            TextLogClass=text_log_cls,
        )
    except Exception as exc:  # pragma: no cover
        msg = "The TUI requires the 'textual' package. Install with: uv add textual or pip install textual"
        raise TextualNotInstalledError(msg) from exc
