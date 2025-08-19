"""Main entry point for the TUI application.

This module provides the run() function that initializes and launches the TUI app.
It handles Textual dependency loading and error handling for the optional UI feature.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn


def run(config: str | Path = "config") -> NoReturn:
    """Entry point to run the TUI application.

    Args:
        config: Path to configuration directory or file

    Raises:
        RuntimeError: If Textual is not installed
        SystemExit: When the application closes
    """
    try:
        from network_toolkit.tui.app import NetworkWorkerApp
    except ImportError as exc:
        msg = (
            "The TUI requires the 'textual' package. "
            "Install with: uv add textual or pip install textual"
        )
        raise RuntimeError(msg) from exc

    try:
        app = NetworkWorkerApp(config_path=config)
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        sys.exit(0)
