"""Clipboard utilities for the TUI with Textual compatibility fallbacks.

Provide a single function to copy to the system clipboard using whatever
mechanism Textual exposes in the current version, falling back safely.
"""

from __future__ import annotations

from typing import Any


def copy_to_clipboard(app: Any, text: str) -> bool:
    """Best-effort copy to system clipboard across Textual versions.

    Returns True if the framework reported success, False otherwise.
    """
    # App helpers
    try:
        if hasattr(app, "copy_to_clipboard"):
            app.copy_to_clipboard(text)
            return True
    except Exception:
        pass
    try:
        if hasattr(app, "set_clipboard"):
            app.set_clipboard(text)
            return True
    except Exception:
        pass
    # Screen helper
    try:
        scr = getattr(app, "screen", None)
        if scr is not None and hasattr(scr, "set_clipboard"):
            scr.set_clipboard(text)
            return True
    except Exception:
        pass
    # Driver helper
    try:
        drv = getattr(app, "driver", None)
        if drv is not None and hasattr(drv, "set_clipboard"):
            drv.set_clipboard(text)
            return True
    except Exception:
        pass
    return False
