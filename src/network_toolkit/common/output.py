# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Output formatting and theming abstraction for Networka."""

from __future__ import annotations

import json
import sys
from enum import Enum
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from network_toolkit.common.styles import StyleManager, StyleName


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

    @property
    def style_manager(self) -> StyleManager:
        """Get the styling for this output manager's console."""
        return self._style_manager

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
            style = self._style_manager.get_style(self._style_name.DEVICE) or ""
            self._console.print(Text.assemble((device, style), f": {message}"))

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
            sys.stdout.write(f"device={device} cmd={command}\n{output}\n")
        else:
            bold_style = self._style_manager.get_style(self._style_name.BOLD) or ""
            self._console.print(Text.assemble(("Device:", bold_style), f" {device}"))
            self._console.print(Text.assemble(("Command:", bold_style), f" {command}"))
            self.print_output(output)

    def _print_status(
        self, label: str, style: StyleName, message: str, context: str | None
    ) -> None:
        status = Text(label, style=self._style_manager.get_style(style) or "")
        if context:
            status.append(" [")
            status.append(
                context,
                style=self._style_manager.get_style(self._style_name.DEVICE) or "",
            )
            status.append("]")
        self._console.print(status, Text(message))

    def print_success(self, message: str, context: str | None = None) -> None:
        """Print a success message."""
        if self.mode != OutputMode.RAW:
            self._print_status("OK", self._style_name.SUCCESS, message, context)

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
        else:
            self._print_status("FAIL", self._style_name.ERROR, message, context)

    def print_warning(self, message: str, context: str | None = None) -> None:
        """Print a warning message."""
        if self.mode == OutputMode.JSON:
            payload: dict[str, Any] = {"type": "warning", "message": message}
            if context:
                payload["device"] = context
            sys.stdout.write(json.dumps(payload) + "\n")
        elif self.mode != OutputMode.RAW:
            self._print_status("WARN", self._style_name.WARNING, message, context)

    def print_info(self, message: str, context: str | None = None) -> None:
        """Print an informational message."""
        if self.mode == OutputMode.JSON:
            payload: dict[str, Any] = {"type": "info", "message": message}
            if context:
                payload["device"] = context
            sys.stdout.write(json.dumps(payload) + "\n")
        elif self.mode != OutputMode.RAW:
            self._console.print(
                f"[{context}] {message}" if context else message, markup=False
            )

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

        bold_style = self._style_manager.get_style(self._style_name.BOLD) or ""
        summary_style = self._style_manager.get_style(self._style_name.SUMMARY) or ""
        self._console.print(
            Text.assemble(
                "\n", ("Run Summary", f"{bold_style} {summary_style}".strip())
            )
        )

        def field(label: str, value: str) -> Text:
            return Text.assemble((f"  {label}:", bold_style), f" {value}")

        group_totals = totals if is_group else None
        target_label = f"{target} (group)" if group_totals is not None else target
        summary_lines = [
            field("Target", target_label),
            field("Type", operation_type),
            field("Operation", name),
        ]
        if group_totals is not None:
            total, succeeded, failed = group_totals
            success_style = (
                self._style_manager.get_style(self._style_name.SUCCESS) or ""
            )
            error_style = self._style_manager.get_style(self._style_name.ERROR) or ""
            devices_line = field("Devices", f"{total} total | ")
            devices_line.append(f"{succeeded} succeeded", style=success_style)
            devices_line.append(", ")
            devices_line.append(f"{failed} failed", style=error_style)
            summary_lines.append(devices_line)
        else:
            summary_lines.append(field("Status", status))
        if results_dir:
            summary_lines.append(field("Results dir", results_dir))
        summary_lines.append(field("Duration", f"{duration:.2f}s"))
        self._console.print(Text("\n").join(summary_lines))

    def print_results_directory(self, results_dir: str) -> None:
        """Print the results directory information."""
        if self.mode == OutputMode.RAW:
            # Raw mode doesn't show results directory info
            return

        style = self._style_manager.get_style(self._style_name.DIM) or ""
        self._console.print(Text(f"\nResults directory: {results_dir}", style=style))

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
            self._console.print(
                Text(
                    text,
                    style=self._style_manager.get_style(self._style_name.OUTPUT) or "",
                )
            )

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
        return self._console.status(Text(message))

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
