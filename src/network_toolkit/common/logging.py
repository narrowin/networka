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


def setup_logging(level: str = "WARNING") -> None:
    """Configure root logging with Rich handler.

    Parameters
    ----------
    level : str
        Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    from network_toolkit.common.output import OutputMode

    # Check if we're in raw mode - if so, disable logging entirely
    output_manager = get_output_manager()
    suppressed_loggers = [
        "scrapli",
        "scrapli.driver",
        "scrapli.channel",
        "scrapli.transport",
        "scrapli_community",
        "network_toolkit.device",
        "network_toolkit.transport",
    ]
    if output_manager.mode == OutputMode.RAW:
        # In raw mode, disable all logging to avoid polluting the output
        # Set the root logger to a very high level to suppress everything
        logging.basicConfig(
            level=logging.CRITICAL + 1,  # Disable all logging
            handlers=[],
            force=True,
        )

        # Also explicitly silence common noisy loggers
        for logger_name in suppressed_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL + 1)
            logger.disabled = True

        return

    # Always pull the current themed console at setup time
    console_obj = output_manager.console

    logging.disable(logging.NOTSET)
    for logger_name in suppressed_loggers:
        logger = logging.getLogger(logger_name)
        logger.disabled = False
        logger.setLevel(logging.NOTSET)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.WARNING),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console_obj, rich_tracebacks=True)],
        force=True,
    )
