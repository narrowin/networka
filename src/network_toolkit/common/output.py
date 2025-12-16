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
        # Import here to avoid circular imports
        from network_toolkit.common.styles import StyleManager, StyleName

        self._style_manager = StyleManager(mode)
        self._style_name = StyleName  # Store reference for use in methods
        self._console = self._style_manager.console

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
            device_part = self._style_manager.format_message(
                device, self._style_name.DEVICE
            )
            self._console.print(f"{device_part}: {message}")

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
            sys.stdout.write(f"{output}\n")
        else:
            # Use style manager for semantic styling
            device_msg = self._style_manager.format_message(
                "Device:", self._style_name.BOLD
            )
            device_msg += f" {device}"
            command_msg = self._style_manager.format_message(
                "Command:", self._style_name.BOLD
            )
            command_msg += f" {command}"
            output_msg = self._style_manager.format_message(
                output, self._style_name.OUTPUT
            )

            self._console.print(device_msg)
            self._console.print(command_msg)
            self._console.print(output_msg)

    def print_success(self, message: str, context: str | None = None) -> None:
        """Print a success message."""
        if self.mode == OutputMode.RAW:
            # In raw mode, suppress all success messages - only show command output
            return
        elif context:
            ok_part = self._style_manager.format_message("OK", self._style_name.SUCCESS)
            context_part = self._style_manager.format_message(
                context, self._style_name.DEVICE
            )
            self._console.print(f"{ok_part} [{context_part}] {message}")
        else:
            ok_part = self._style_manager.format_message("OK", self._style_name.SUCCESS)
            self._console.print(f"{ok_part} {message}")

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
            fail_part = self._style_manager.format_message(
                "FAIL", self._style_name.ERROR
            )
            context_part = self._style_manager.format_message(
                context, self._style_name.DEVICE
            )
            self._console.print(f"{fail_part} [{context_part}] {message}")
        else:
            fail_part = self._style_manager.format_message(
                "FAIL", self._style_name.ERROR
            )
            self._console.print(f"{fail_part} {message}")

    def print_warning(self, message: str, context: str | None = None) -> None:
        """Print a warning message."""
        if self.mode == OutputMode.JSON:
            payload: dict[str, Any] = {"type": "warning", "message": message}
            if context:
                payload["device"] = context
            sys.stdout.write(json.dumps(payload) + "\n")
        elif self.mode == OutputMode.RAW:
            # In raw mode, suppress all warning messages - only show command output
            return
        elif context:
            warn_part = self._style_manager.format_message(
                "WARN", self._style_name.WARNING
            )
            context_part = self._style_manager.format_message(
                context, self._style_name.DEVICE
            )
            self._console.print(f"{warn_part} [{context_part}] {message}")
        else:
            warn_part = self._style_manager.format_message(
                "WARN", self._style_name.WARNING
            )
            self._console.print(f"{warn_part} {message}")

    def print_info(self, message: str, context: str | None = None) -> None:
        """Print an informational message."""
        if self.mode == OutputMode.JSON:
            payload: dict[str, Any] = {"type": "info", "message": message}
            if context:
                payload["device"] = context
            sys.stdout.write(json.dumps(payload) + "\n")
        elif self.mode == OutputMode.RAW:
            # In raw mode, suppress all info messages - only show command output
            return
        elif context:
            self._console.print(f"[{context}] {message}")
        else:
            self._console.print(f"{message}")

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

        # Use style manager for the header
        header = self._style_manager.format_message(
            "Run Summary", self._style_name.SUMMARY
        )
        header = self._style_manager.format_message(header, self._style_name.BOLD)
        self._console.print(f"\n{header}")

        if is_group and totals:
            total, succeeded, failed = totals

            # Build styled summary for group
            target_line = (
                self._style_manager.format_message("Target:", self._style_name.BOLD)
                + f" {target} (group)"
            )
            type_line = (
                self._style_manager.format_message("Type:", self._style_name.BOLD)
                + f" {operation_type}"
            )
            operation_line = (
                self._style_manager.format_message("Operation:", self._style_name.BOLD)
                + f" {name}"
            )
            devices_line = (
                self._style_manager.format_message("Devices:", self._style_name.BOLD)
                + f" {total} total | "
            )

            # Add success/failure counts with semantic styling
            success_text = self._style_manager.format_message(
                f"{succeeded} succeeded", self._style_name.SUCCESS
            )
            error_text = self._style_manager.format_message(
                f"{failed} failed", self._style_name.ERROR
            )
            devices_line += f"{success_text}, {error_text}"

            summary_lines = [
                f"  {target_line}",
                f"  {type_line}",
                f"  {operation_line}",
                f"  {devices_line}",
            ]

            if results_dir:
                results_line = (
                    self._style_manager.format_message(
                        "Results dir:", self._style_name.BOLD
                    )
                    + f" {results_dir}"
                )
                summary_lines.append(f"  {results_line}")

            duration_line = (
                self._style_manager.format_message("Duration:", self._style_name.BOLD)
                + f" {duration:.2f}s"
            )
            summary_lines.append(f"  {duration_line}")

            self._console.print("\n".join(summary_lines))
        else:
            # Build styled summary for single device
            target_line = (
                self._style_manager.format_message("Target:", self._style_name.BOLD)
                + f" {target}"
            )
            type_line = (
                self._style_manager.format_message("Type:", self._style_name.BOLD)
                + f" {operation_type}"
            )
            operation_line = (
                self._style_manager.format_message("Operation:", self._style_name.BOLD)
                + f" {name}"
            )
            status_line = (
                self._style_manager.format_message("Status:", self._style_name.BOLD)
                + f" {status}"
            )

            summary_lines = [
                f"  {target_line}",
                f"  {type_line}",
                f"  {operation_line}",
                f"  {status_line}",
            ]

            if results_dir:
                results_line = (
                    self._style_manager.format_message(
                        "Results dir:", self._style_name.BOLD
                    )
                    + f" {results_dir}"
                )
                summary_lines.append(f"  {results_line}")

            duration_line = (
                self._style_manager.format_message("Duration:", self._style_name.BOLD)
                + f" {duration:.2f}s"
            )
            summary_lines.append(f"  {duration_line}")

            self._console.print("\n".join(summary_lines))

    def print_results_directory(self, results_dir: str) -> None:
        """Print the results directory information."""
        if self.mode == OutputMode.RAW:
            # Raw mode doesn't show results directory info
            return

        # Use style manager for dim styling
        msg = self._style_manager.format_message(
            f"Results directory: {results_dir}", self._style_name.DIM
        )
        self._console.print(f"\n{msg}")

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
            styled_text = self._style_manager.format_message(
                text, self._style_name.OUTPUT
            )
            self._console.print(styled_text)

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
            transport_label = self._style_manager.format_message(
                "Transport:", self._style_name.TRANSPORT
            )
            self._console.print(f"{transport_label} {transport_type}")

    def print_running_command(self, command: str) -> None:
        """Print information about a running command."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"running={command}\n")
        else:
            running_label = self._style_manager.format_message(
                "Running:", self._style_name.RUNNING
            )
            self._console.print(f"{running_label} {command}")

    def print_connection_status(self, device: str, connected: bool) -> None:
        """Print connection status."""
        if self.mode == OutputMode.RAW:
            status = "connected" if connected else "failed"
            sys.stdout.write(f"device={device} status={status}\n")
        elif connected:
            ok_part = self._style_manager.format_message(
                "OK", self._style_name.CONNECTED
            )
            self._console.print(f"{ok_part} Connected to {device}")
        else:
            fail_part = self._style_manager.format_message(
                "FAIL", self._style_name.FAILED
            )
            self._console.print(f"{fail_part} Failed to connect to {device}")

    def print_downloading(self, device: str, filename: str) -> None:
        """Print download progress."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"device={device} downloading={filename}\n")
        else:
            message = f"Downloading {filename} from {device}..."
            styled_message = self._style_manager.format_message(
                message, self._style_name.DOWNLOADING
            )
            self._console.print(styled_message)

    def print_credential_info(self, message: str) -> None:
        """Print credential-related information."""
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"credential: {message}\n")
        else:
            styled_message = self._style_manager.format_message(
                message, self._style_name.CREDENTIAL
            )
            self._console.print(styled_message)

    def print_unknown_warning(self, unknowns: list[str]) -> None:
        """Print warning about unknown targets."""
        unknowns_str = ", ".join(unknowns)
        if self.mode == OutputMode.RAW:
            sys.stdout.write(f"warning: unknown targets: {unknowns_str}\n")
        else:
            message = f"Warning: Unknown targets: {unknowns_str}"
            styled_message = self._style_manager.format_message(
                message, self._style_name.UNKNOWN
            )
            self._console.print(styled_message)


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
