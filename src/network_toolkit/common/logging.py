# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Shared logging and console utilities for the Network Toolkit."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler

# Rich console for pretty output across the CLI
console = Console()


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging with Rich handler.

    Parameters
    ----------
    level : str
        Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
