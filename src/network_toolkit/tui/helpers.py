"""Helper utilities for the Textual UI.

This module contains small, UI-adjacent helpers that don't require importing
Textual at module import time. Keep dependencies minimal.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

try:  # optional rich
    from rich.markup import escape as _escape_markup
except Exception:  # pragma: no cover - rich optional
    _escape_markup = None  # type: ignore[assignment]


def log_write(log_widget: Any, message: str) -> None:
    """Best-effort write to a Textual Log/RichLog-like widget.

    Accepts multiple widget API shapes across Textual versions.
    """
    try:
        msg = str(message)
        # Escape markup if the widget interprets Rich markup to avoid injection
        if _escape_markup is not None:
            msg = _escape_markup(msg)
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


def collect_non_empty_lines(text: str | None) -> list[str]:
    """Return non-empty trimmed lines from text."""
    if not text:
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def first(iterable: Iterable[str]) -> str | None:
    """Return first element or None."""
    for item in iterable:
        return item
    return None
