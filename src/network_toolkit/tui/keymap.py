"""Keymap definition for the TUI.

This module keeps a data-only representation of key bindings so that
`app.py` can transform them into Textual `Binding`s via the compat layer.
"""

from __future__ import annotations

from typing import NamedTuple


class KeyBinding(NamedTuple):
    key: str
    action: str
    description: str
    show: bool = False
    key_display: str | None = None
    priority: bool = False


# Default keymap for the TUI
KEYMAP: list[KeyBinding] = [
    KeyBinding("q", "quit", "Quit", True),
    KeyBinding("enter", "confirm", "Run"),
    KeyBinding("r", "confirm", "Run"),
    KeyBinding("ctrl+c", "quit", "Quit"),
    # Priority toggles so they work during input and runs
    KeyBinding("s", "toggle_summary", "Summary", True, None, True),
    KeyBinding("o", "toggle_output", "Output", True, None, True),
    KeyBinding("f", "focus_filter", "Focus filter", True, None, True),
    KeyBinding("t", "toggle_theme", "Theme", True, None, True),
    KeyBinding("f2", "toggle_summary", "Summary"),
    # Copy helpers
    KeyBinding("y", "copy_last_error", "Copy last error", True, None, True),
    KeyBinding("ctrl+y", "copy_status", "Copy status", True, None, True),
]
