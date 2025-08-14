# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Output formatting and theming abstraction for the Network Toolkit."""

from __future__ import annotations

import json
import sys
from enum import Enum
from typing import Any

from rich.console import Console
from rich.theme import Theme


class OutputMode(str, Enum):
    """Output decoration modes for the CLI."""

    NORMAL = "normal"
    LIGHT = "light"
    DARK = "dark"
    NO_COLOR = "no-color"
    RAW = "raw"


class OutputManager:
    """Manages output formatting and theming across the application.

    This class provides an abstraction layer for all output operations,
    supporting different modes like light/dark themes, no-color mode,
    and raw output mode.
    """

    def __init__(self, mode: OutputMode = OutputMode.NORMAL) -> None:
        """Initialize the output manager with a specific mode.

        Parameters
        ----------
        mode : OutputMode
            The output mode to use for formatting
        """
        self.mode = mode
        self._console = self._create_console()

    def _create_console(self) -> Console:
        """Create a console instance based on the current mode."""
        if self.mode == OutputMode.RAW:
            # Raw mode uses no styling at all
            return Console(
                color_system=None,
                force_terminal=False,
                stderr=False,
                file=sys.stdout,
                width=None,
                height=None
            )
        elif self.mode == OutputMode.NO_COLOR:
            # No color mode disables colors but keeps other formatting
            return Console(
                color_system=None,
                force_terminal=True,
                stderr=False
            )
        elif self.mode == OutputMode.LIGHT:
            # Light theme with appropriate colors
            light_theme = Theme({
                "info": "blue",
                "warning": "dark_orange",
                "error": "red",
                "success": "green",
                "device": "cyan",
                "command": "magenta",
                "output": "default",
                "summary": "blue",
                "dim": "dim",
                "bold": "bold"
            })
            return Console(
                theme=light_theme,
                stderr=False,
                force_terminal=True,
                color_system="standard"
            )
        elif self.mode == OutputMode.DARK:
            # Dark theme with appropriate colors
            dark_theme = Theme({
                "info": "bright_blue",
                "warning": "yellow",
                "error": "bright_red",
                "success": "bright_green",
                "device": "bright_cyan",
                "command": "bright_magenta",
                "output": "white",
                "summary": "bright_blue",
                "dim": "dim",
                "bold": "bold"
            })
            return Console(
                theme=dark_theme,
                stderr=False,
                force_terminal=True,
                color_system="standard"
            )
        else:
            # Normal mode uses default Rich styling
            return Console(stderr=False)

    @property
    def console(self) -> Console:
        """Get the console instance."""
        return self._console

    def print_device_info(self, device: str, message: str) -> None:
        """Print device-related information."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"device={device} {message}\n")
        else:
            self._console.print(f"[device]{device}[/device]: {message}")

    def print_command_output(self, device: str, command: str, output: str) -> None:
        """Print command output with appropriate formatting."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"device={device} cmd={command}\n")
            sys.stdout.write(f"{output}\n")
        else:
            self._console.print(f"[bold device]Device:[/bold device] {device}")
            self._console.print(f"[bold command]Command:[/bold command] {command}")
            self._console.print(f"[output]{output}[/output]")

    def print_success(self, message: str, context: str | None = None) -> None:
        """Print a success message."""
        if self.mode == OutputMode.RAW:
            if context:
                sys.stdout.write(f"device={context} success: {message}\n")
            else:
                sys.stdout.write(f"success: {message}\n")
        elif context:
            self._console.print(f"[success]✓[/success] [{context}] {message}")
        else:
            self._console.print(f"[success]✓[/success] {message}")

    def print_error(self, message: str, context: str | None = None) -> None:
        """Print an error message."""
        if self.mode == OutputMode.RAW:
            if context:
                sys.stdout.write(f"device={context} error: {message}\n")
            else:
                sys.stdout.write(f"error: {message}\n")
        elif context:
            self._console.print(f"[error]✗[/error] [{context}] {message}")
        else:
            self._console.print(f"[error]✗[/error] {message}")

    def print_warning(self, message: str, context: str | None = None) -> None:
        """Print a warning message."""
        if self.mode == OutputMode.RAW:
            if context:
                sys.stdout.write(f"device={context} warning: {message}\n")
            else:
                sys.stdout.write(f"warning: {message}\n")
        elif context:
            self._console.print(f"[warning]⚠[/warning] [{context}] {message}")
        else:
            self._console.print(f"[warning]⚠[/warning] {message}")

    def print_info(self, message: str, context: str | None = None) -> None:
        """Print an informational message."""
        if self.mode == OutputMode.RAW:
            if context:
                sys.stdout.write(f"device={context} info: {message}\n")
            else:
                sys.stdout.write(f"info: {message}\n")
        elif context:
            self._console.print(f"[info]i[/info] [{context}] {message}")
        else:
            self._console.print(f"[info]i[/info] {message}")

    def print_summary(
        self,
        *,
        target: str,
        operation_type: str,
        name: str,
        duration: float,
        status: str = "Success",
        is_group: bool = False,
        totals: tuple[int, int, int] | None = None,
        results_dir: str | None = None
    ) -> None:
        """Print a run summary."""
        if self.mode == OutputMode.RAW:
            # Raw mode skips summaries entirely
            return

        self._console.print("\n[bold summary]Run Summary[/bold summary]")

        if is_group and totals:
            total, succeeded, failed = totals
            self._console.print(
                f"  [bold]Target:[/bold] {target} (group)\n"
                f"  [bold]Type:[/bold] {operation_type}\n"
                f"  [bold]Operation:[/bold] {name}\n"
                f"  [bold]Devices:[/bold] {total} total | "
                f"[success]{succeeded} succeeded[/success], "
                f"[error]{failed} failed[/error]\n"
                + (f"  [bold]Results dir:[/bold] {results_dir}\n" if results_dir else "")
                + f"  [bold]Duration:[/bold] {duration:.2f}s"
            )
        else:
            self._console.print(
                f"  [bold]Target:[/bold] {target}\n"
                f"  [bold]Type:[/bold] {operation_type}\n"
                f"  [bold]Operation:[/bold] {name}\n"
                f"  [bold]Status:[/bold] {status}\n"
                + (f"  [bold]Results dir:[/bold] {results_dir}\n" if results_dir else "")
                + f"  [bold]Duration:[/bold] {duration:.2f}s"
            )

    def print_results_directory(self, results_dir: str) -> None:
        """Print the results directory information."""
        if self.mode == OutputMode.RAW:
            # Raw mode doesn't show results directory info
            return

        self._console.print(f"\n[dim]Results directory: {results_dir}[/dim]")

    def print_json(self, data: dict[str, Any]) -> None:
        """Print JSON data."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"{json.dumps(data)}\n")
        else:
            self._console.print_json(json.dumps(data))

    def print_separator(self) -> None:
        """Print a separator line."""
        if self.mode == OutputMode.RAW:
            # Raw mode doesn't use separators
            return

        if self.mode == OutputMode.NO_COLOR:
            self._console.print("-" * 80)
        else:
            self._console.rule()


def get_output_mode_from_env() -> OutputMode:
    """Determine output mode from environment variables.

    Respects standard environment variables like NO_COLOR and FORCE_COLOR,
    as well as custom NT_OUTPUT_MODE.

    Returns
    -------
    OutputMode
        The appropriate output mode based on environment
    """
    import os

    # Check for NO_COLOR first (standard)
    if os.getenv("NO_COLOR"):
        return OutputMode.NO_COLOR

    # Check for custom output mode
    output_mode = os.getenv("NT_OUTPUT_MODE", "").lower()
    if output_mode in OutputMode.__members__.values():
        return OutputMode(output_mode)

    # Check for theme preference
    if output_mode in ["light", "dark"]:
        return OutputMode(output_mode)

    # Default to normal mode
    return OutputMode.NORMAL


# Global output manager instance - managed through functions
_output_manager: OutputManager | None = None


def get_output_manager() -> OutputManager:
    """Get the global output manager instance."""
    global _output_manager  # noqa: PLW0603
    if _output_manager is None:
        mode = get_output_mode_from_env()
        _output_manager = OutputManager(mode)
    return _output_manager


def set_output_mode(mode: OutputMode) -> OutputManager:
    """Set the global output mode and return the new manager."""
    manager = OutputManager(mode)
    # Store the manager globally for consistency
    # Using global here is acceptable for a singleton pattern
    global _output_manager  # noqa: PLW0603
    _output_manager = manager
    return manager


def print_device_output(device: str, command: str, output: str) -> None:
    """Convenience function for printing device command output."""
    get_output_manager().print_command_output(device, command, output)


def print_success(message: str, context: str | None = None) -> None:
    """Convenience function for printing success messages."""
    get_output_manager().print_success(message, context)


def print_error(message: str, context: str | None = None) -> None:
    """Convenience function for printing error messages."""
    get_output_manager().print_error(message, context)


def print_warning(message: str, context: str | None = None) -> None:
    """Convenience function for printing warning messages."""
    get_output_manager().print_warning(message, context)


def print_info(message: str, context: str | None = None) -> None:
    """Convenience function for printing info messages."""
    get_output_manager().print_info(message, context)
