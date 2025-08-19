"""Modern Textual-based TUI for Network Worker (nw).

A clean, maintainable TUI implementation following modern Textual best practices.

Architecture:
- Clean separation of concerns with dedicated widgets
- Reactive state management
- Comprehensive type safety
- External CSS styling
- Robust error handling
- High testability

Design Goals:
- Keep TUI isolated from core CLI (no imports from here in CLI paths)
- Lazy-import Textual for optional dependency support
- Modern, maintainable codebase following best practices
"""

from __future__ import annotations

__all__ = [
    "run",
]

from network_toolkit.tui.main import run  # re-export for console script
