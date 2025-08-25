# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Shared logging and console utilities for the Network Toolkit."""

from __future__ import annotations

import logging

from rich.logging import RichHandler

# Use the centralized OutputManager console so logging respects output mode
from network_toolkit.common.output import get_output_manager


class _DynamicConsoleProxy:
    """Proxy that forwards to the current OutputManager console.

    Some modules import `console` from this module; keep a dynamic proxy so the
    active output mode is respected and we don't freeze a console at import time.
    """

    def __getattr__(self, name: str) -> object:
        return getattr(get_output_manager().console, name)


# Public console handle for convenience/legacy imports
console = _DynamicConsoleProxy()


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging with Rich handler.

    Parameters
    ----------
    level : str
        Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Always pull the current themed console at setup time
    console_obj = get_output_manager().console

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console_obj, rich_tracebacks=True)],
    )
