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
from rich.table import Table
from rich.theme import Theme


class OutputMode(str, Enum):
    """Output decoration modes for the CLI."""

    DEFAULT = "default"  # Rich's default styling
    LIGHT = "light"  # Custom light theme (dark colors on light background)
    DARK = "dark"  # Custom dark theme (bright colors on dark background)
    NO_COLOR = "no-color"  # No colors, structured output only
    RAW = "raw"  # Machine-readable text, minimal formatting
    JSON = "json"  # Machine-readable JSONL events per line


class OutputManager:
    """Manages output formatting and theming across the application.

    This class provides an abstraction layer for all output operations,
    supporting different modes like light/dark themes, no-color mode,
    and raw output mode.
    """

    def __init__(self, mode: OutputMode = OutputMode.DEFAULT) -> None:
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
        if self.mode in (OutputMode.RAW, OutputMode.JSON):
            # Raw/JSON modes use no styling at all
            return Console(
                color_system=None,
                force_terminal=False,
                stderr=False,
                file=sys.stdout,
                width=None,
                height=None,
            )
        elif self.mode == OutputMode.NO_COLOR:
            # No color mode disables colors but keeps other formatting
            return Console(color_system=None, force_terminal=True, stderr=False)
        elif self.mode == OutputMode.LIGHT:
            # Light-optimized: stronger contrast on light terminals
            light_theme = Theme(
                {
                    "info": "blue",
                    "warning": "yellow",
                    "error": "red",
                    "success": "green",
                    "device": "cyan",
                    "command": "magenta",
                    # Ensure readable plain output on light backgrounds
                    "output": "#000000",
                    "summary": "blue",
                    # Avoid washed-out text on light themes
                    "dim": "default",
                    "bold": "bold",
                    "transport": "magenta",
                    "running": "blue",
                    "connected": "green",
                    "failed": "red",
                    "downloading": "cyan",
                    "credential": "cyan",
                    "unknown": "yellow",
                }
            )
            return Console(theme=light_theme, stderr=False, force_terminal=True)
        elif self.mode == OutputMode.DARK:
            # Dark uses defaults; also avoid dim to keep consistency
            dark_theme = Theme(
                {
                    "info": "blue",
                    "warning": "yellow",
                    "error": "red",
                    "success": "green",
                    "device": "cyan",
                    "command": "magenta",
                    "output": "default",
                    "summary": "blue",
                    "dim": "default",
                    "bold": "bold",
                    "transport": "magenta",
                    "running": "blue",
                    "connected": "green",
                    "failed": "red",
                    "downloading": "cyan",
                    "credential": "cyan",
                    "unknown": "yellow",
                }
            )
            return Console(theme=dark_theme, stderr=False, force_terminal=True)
        else:
            # Default mode uses Rich's default styling with our semantic colors
            default_theme = Theme(
                {
                    "info": "blue",
                    "warning": "yellow",
                    "error": "red",
                    "success": "green",
                    "device": "cyan",
                    "command": "magenta",
                    "output": "default",
                    "summary": "blue",
                    # Avoid dim across themes for readability on light backgrounds
                    "dim": "default",
                    "bold": "bold",
                    # Additional semantic colors for all use cases
                    "transport": "magenta",
                    "running": "blue",
                    "connected": "green",
                    "failed": "red",
                    "downloading": "cyan",
                    "credential": "cyan",
                    "unknown": "yellow",
                }
            )
            return Console(theme=default_theme, stderr=False, force_terminal=True)

    @property
    def console(self) -> Console:
        """Get the console instance."""
        return self._console

    def print_device_info(self, device: str, message: str) -> None:
        """Print device-related information."""
        if self.mode == OutputMode.JSON:
            sys.stdout.write(
                json.dumps(
                    {
                        "type": "info",
                        "device": device,
                        "message": message,
                    }
                )
                + "\n"
            )
        elif self.mode == OutputMode.RAW:
            sys.stdout.write(f"device={device} {message}\n")
        else:
            self._console.print(f"[device]{device}[/device]: {message}")

    def print_command_output(self, device: str, command: str, output: str) -> None:
        """Print command output with appropriate formatting."""
        if self.mode == OutputMode.JSON:
            sys.stdout.write(
                json.dumps(
                    {
                        "type": "output",
                        "device": device,
                        "command": command,
                        "message": output,
                    }
                )
                + "\n"
            )
        elif self.mode == OutputMode.RAW:
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
            self._console.print(f"[success]OK[/success] [{context}] {message}")
        else:
            self._console.print(f"[success]OK[/success] {message}")

    def print_error(self, message: str, context: str | None = None) -> None:
        """Print an error message."""
        if self.mode == OutputMode.JSON:
            payload: dict[str, Any] = {"type": "error", "message": message}
            if context:
                payload["device"] = context
            sys.stdout.write(json.dumps(payload) + "\n")
        elif self.mode == OutputMode.RAW:
            if context:
                sys.stdout.write(f"device={context} error: {message}\n")
            else:
                sys.stdout.write(f"error: {message}\n")
        elif context:
            self._console.print(f"[error]FAIL[/error] [{context}] {message}")
        else:
            self._console.print(f"[error]FAIL[/error] {message}")

    def print_warning(self, message: str, context: str | None = None) -> None:
        """Print a warning message."""
        if self.mode == OutputMode.JSON:
            payload: dict[str, Any] = {"type": "warning", "message": message}
            if context:
                payload["device"] = context
            sys.stdout.write(json.dumps(payload) + "\n")
        elif self.mode == OutputMode.RAW:
            if context:
                sys.stdout.write(f"device={context} warning: {message}\n")
            else:
                sys.stdout.write(f"warning: {message}\n")
        elif context:
            self._console.print(f"[warning]WARN[/warning] [{context}] {message}")
        else:
            self._console.print(f"[warning]WARN[/warning] {message}")

    def print_info(self, message: str, context: str | None = None) -> None:
        """Print an informational message."""
        if self.mode == OutputMode.JSON:
            payload: dict[str, Any] = {"type": "info", "message": message}
            if context:
                payload["device"] = context
            sys.stdout.write(json.dumps(payload) + "\n")
        elif self.mode == OutputMode.RAW:
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
        results_dir: str | None = None,
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
                + (
                    f"  [bold]Results dir:[/bold] {results_dir}\n"
                    if results_dir
                    else ""
                )
                + f"  [bold]Duration:[/bold] {duration:.2f}s"
            )
        else:
            self._console.print(
                f"  [bold]Target:[/bold] {target}\n"
                f"  [bold]Type:[/bold] {operation_type}\n"
                f"  [bold]Operation:[/bold] {name}\n"
                f"  [bold]Status:[/bold] {status}\n"
                + (
                    f"  [bold]Results dir:[/bold] {results_dir}\n"
                    if results_dir
                    else ""
                )
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

    def print_blank_line(self) -> None:
        """Print a single blank line (no-op in raw mode)."""
        if self.mode == OutputMode.RAW:
            return
        self._console.print()

    def print_output(self, text: str) -> None:
        """Print plain command output using the standardized 'output' style.

        In RAW mode, prints the text as-is to stdout without styling.
        """
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"{text}\n")
        else:
            self._console.print(f"[output]{text}[/output]")

    def create_table(
        self, *, title: str = "", show_header: bool = False, box: Any | None = None
    ) -> Table:
        """Create a Rich Table consistent with the current output mode.

        Parameters
        ----------
        title : str
            Optional title to display above the table.
        show_header : bool
            Whether to show a header row.
        box : Any | None
            The box style to use (e.g., box.SIMPLE). Defaults to None (no box),
            mirroring existing usage in commands.
        """
        return Table(title=title, show_header=show_header, box=box)

    def print_table(self, table: Table) -> None:
        """Print a Rich Table (no-op in raw mode)."""
        if self.mode == OutputMode.RAW:
            return
        self._console.print(table)

    def print_text(self, text: str) -> None:
        """Print arbitrary rich-markup text using the current console.

        Use this sparingly for help screens or pre-formatted content.
        """
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"{text}\n")
        else:
            self._console.print(text)

    def status(self, message: str) -> Any:
        """Return a status/spinner context manager bound to this console.

        Example:
            with output.status("Working..."):
                ...
        """
        return self._console.status(message)

    def print_transport_info(self, transport_type: str) -> None:
        """Print transport information."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"transport={transport_type}\n")
        else:
            self._console.print(f"[transport]Transport:[/transport] {transport_type}")

    def print_running_command(self, command: str) -> None:
        """Print information about a running command."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"running={command}\n")
        else:
            self._console.print(f"[running]Running:[/running] {command}")

    def print_connection_status(self, device: str, connected: bool) -> None:
        """Print connection status."""
        if self.mode == OutputMode.RAW:
            status = "connected" if connected else "failed"
            sys.stdout.write(f"device={device} status={status}\n")
        elif connected:
            self._console.print(f"[connected]OK Connected to {device}[/connected]")
        else:
            self._console.print(f"[failed]FAIL Failed to connect to {device}[/failed]")

    def print_downloading(self, device: str, filename: str) -> None:
        """Print download progress."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"device={device} downloading={filename}\n")
        else:
            self._console.print(
                f"[downloading]Downloading {filename} from {device}...[/downloading]"
            )

    def print_credential_info(self, message: str) -> None:
        """Print credential-related information."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"credential: {message}\n")
        else:
            self._console.print(f"[credential]{message}[/credential]")

    def print_unknown_warning(self, unknowns: list[str]) -> None:
        """Print warning about unknown targets."""
        unknowns_str = ", ".join(unknowns)
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"warning: unknown targets: {unknowns_str}\n")
        else:
            self._console.print(
                f"[unknown]Warning: Unknown targets: {unknowns_str}[/unknown]"
            )


def get_output_mode_from_env() -> OutputMode:
    """Determine output mode from environment variables.

    Respects standard environment variables like NO_COLOR and the custom
    NW_OUTPUT_MODE environment variable.

    Returns
    -------
    OutputMode
        The appropriate output mode based on environment
    """
    import os

    # Check for NO_COLOR first (standard)
    if os.getenv("NO_COLOR"):
        return OutputMode.NO_COLOR

    # Check for custom output mode environment variable (new scheme)
    output_mode = os.getenv("NW_OUTPUT_MODE", "").lower()
    valid_values = {m.value for m in OutputMode}
    if output_mode and output_mode in valid_values:
        return OutputMode(output_mode)

    # Default to default mode
    return OutputMode.DEFAULT


def get_output_mode_from_config(config_output_mode: str | None = None) -> OutputMode:
    """Determine output mode from config, with environment variable override.

    Parameters
    ----------
    config_output_mode : str | None
        The output mode from the config file, if any

    Returns
    -------
    OutputMode
        The appropriate output mode based on config and environment
    """
    import os

    # Environment variables always take precedence
    # Check for NO_COLOR first (standard)
    if os.getenv("NO_COLOR"):
        return OutputMode.NO_COLOR

    # Check for custom output mode environment variable (new scheme)
    env_output_mode = os.getenv("NW_OUTPUT_MODE", "").lower()
    valid_values = {m.value for m in OutputMode}
    if env_output_mode and env_output_mode in valid_values:
        return OutputMode(env_output_mode)

    # Use config setting if available
    if config_output_mode and config_output_mode.lower() in valid_values:
        return OutputMode(config_output_mode.lower())

    # Default to default mode
    return OutputMode.DEFAULT


# Global output manager instance - simple singleton
_output_manager: OutputManager | None = None


def get_output_manager() -> OutputManager:
    """Get the global output manager instance."""
    global _output_manager  # noqa: PLW0603
    if _output_manager is None:
        mode = get_output_mode_from_env()
        _output_manager = OutputManager(mode)
    return _output_manager


def get_output_manager_with_config(
    config_output_mode: str | None = None,
) -> OutputManager:
    """Get output manager with config-based mode resolution.

    This creates a new manager each time to respect current environment state.
    """
    mode = get_output_mode_from_config(config_output_mode)
    return OutputManager(mode)


def set_output_mode(mode: OutputMode) -> OutputManager:
    """Set the global output mode and return the new manager."""
    global _output_manager  # noqa: PLW0603
    _output_manager = OutputManager(mode)
    return _output_manager


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
