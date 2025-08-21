# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Centralized error handling and message formatting utilities."""

from __future__ import annotations

from typing import Any

from rich.console import Console

from network_toolkit.common.styles import StyleManager, StyleName
from network_toolkit.common.output import OutputMode


def format_error_message(
    error: str, details: dict[str, Any] | None = None, context: str | None = None
) -> str:
    """Format consistent error messages across the toolkit.

    Parameters
    ----------
    error : str
        Main error message
    details : dict[str, Any] | None
        Optional error details
    context : str | None
        Optional context (device name, command, etc.)

    Returns
    -------
    str
        Formatted error message
    """
    if context:
        message = f"[{context}] {error}"
    else:
        message = error

    if details:
        detail_parts = [f"{k}={v}" for k, v in details.items()]
        message += f" ({', '.join(detail_parts)})"

    return message


def print_error(
    console: Console,
    error: str,
    details: dict[str, Any] | None = None,
    context: str | None = None,
    exit_code: int | None = None,
) -> None:
    """Print a formatted error message to console.

    Parameters
    ----------
    console : Console
        Rich console instance
    error : str
        Main error message
    details : dict[str, Any] | None
        Optional error details
    context : str | None
        Optional context (device name, command, etc.)
    exit_code : int | None
        If provided, will exit with this code
    """
    message = format_error_message(error, details, context)
    # Use default theme for error display in legacy functions
    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    styled_message = style_manager.format_message(f"Error: {message}", StyleName.ERROR)
    console.print(styled_message)

    if exit_code is not None:
        raise SystemExit(exit_code)


def print_warning(
    console: Console,
    warning: str,
    details: dict[str, Any] | None = None,
    context: str | None = None,
) -> None:
    """Print a formatted warning message to console.

    Parameters
    ----------
    console : Console
        Rich console instance
    warning : str
        Main warning message
    details : dict[str, Any] | None
        Optional warning details
    context : str | None
        Optional context (device name, command, etc.)
    """
    message = format_error_message(warning, details, context)
    # Use default theme for warning display in legacy functions
    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    styled_message = style_manager.format_message(f"Warning: {message}", StyleName.WARNING)
    console.print(styled_message)


def print_success(
    console: Console,
    message: str,
    details: dict[str, Any] | None = None,
    context: str | None = None,
) -> None:
    """Print a formatted success message to console.

    Parameters
    ----------
    console : Console
        Rich console instance
    message : str
        Main success message
    details : dict[str, Any] | None
        Optional success details
    context : str | None
        Optional context (device name, command, etc.)
    """
    formatted = format_error_message(message, details, context)
    # Use default theme for success display in legacy functions
    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    styled_message = style_manager.format_message(formatted, StyleName.SUCCESS)
    console.print(styled_message)
