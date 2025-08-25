"""Textual-based TUI for Network Worker (nw).

This package contains an optional Textual UI that lets users select
devices/groups on the left and sequences/commands on the right.

Design goals:
- Keep TUI isolated from core CLI and libraries (no imports from here in CLI paths)
- Lazy-import Textual so normal CLI usage doesn't require the dependency
- Provide a simple first iteration that focuses on selection UX; execution comes later
"""

from __future__ import annotations

__all__ = [
    "run",
]

from network_toolkit.tui.app import run  # re-export for console script
