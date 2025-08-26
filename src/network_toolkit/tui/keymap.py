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
    KeyBinding("q", "close_overlays", "Close panel", True, None, True),
    KeyBinding("ctrl+c", "cancel", "Cancel run", True, None, True),
    KeyBinding("h", "toggle_help", "Help", True, None, True),
    KeyBinding("r", "confirm", "Run"),
    # Priority toggles so they work during input and runs
    KeyBinding("s", "toggle_summary", "Summary", True, None, True),
    KeyBinding("o", "toggle_output", "Output", True, None, True),
    KeyBinding("t", "toggle_theme", "Theme", True, None, True),
]
