# SPDX-License-Identifier: MIT
"""Helper utilities for consistent command styling and output."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputMode,
    get_output_manager,
    get_output_manager_with_config,
    set_output_mode,
)
from network_toolkit.common.styles import StyleManager
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def create_standard_options() -> dict[str, object]:
    """Create standard CLI options that most commands need."""
    return {
        "config_file": Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ],
        "output_mode": Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ],
        "verbose": Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ],
    }


class CommandContext:
    """Context object that provides styled output and error handling for commands."""

    def __init__(
        self,
        output_mode: OutputMode | None = None,
        verbose: bool = False,
        config_file: Path | None = None,
    ):
        """Initialize command context with output styling."""
        self.verbose = verbose
        self.config_file = config_file or DEFAULT_CONFIG_PATH

        # Set up logging
        setup_logging("DEBUG" if verbose else "INFO")

        # Handle output mode configuration
        if output_mode is not None:
            set_output_mode(output_mode)
            self.output_manager = get_output_manager()
        else:
            # Try to use config-based output mode if config exists
            try:
                config = load_config(self.config_file)
                self.output_manager = get_output_manager_with_config(
                    config.general.output_mode
                )
            except Exception:
                # Fall back to default if config loading fails
                self.output_manager = get_output_manager()

        # Create style manager for themed output
        self.style_manager = StyleManager(self.output_manager.mode)

        # Expose commonly used objects
        self.console = self.style_manager.console
        self.mode = self.output_manager.mode

    def print_error(self, message: str, device_name: str | None = None) -> None:
        """Print an error message with proper styling."""
        self.output_manager.print_error(message, device_name)

    def print_warning(self, message: str, device_name: str | None = None) -> None:
        """Print a warning message with proper styling."""
        from network_toolkit.common.styles import StyleName

        styled_message = self.style_manager.format_message(message, StyleName.WARNING)
        self.console.print(styled_message)

    def print_success(self, message: str, device_name: str | None = None) -> None:
        """Print a success message with proper styling."""
        from network_toolkit.common.styles import StyleName

        styled_message = self.style_manager.format_message(message, StyleName.SUCCESS)
        self.console.print(styled_message)

    def print_info(self, message: str, device_name: str | None = None) -> None:
        """Print an info message with proper styling."""
        from network_toolkit.common.styles import StyleName

        styled_message = self.style_manager.format_message(message, StyleName.INFO)
        self.console.print(styled_message)

    def handle_error(self, error: Exception) -> None:
        """Handle exceptions with proper styled output and exit."""
        if isinstance(error, NetworkToolkitError):
            self.print_error(f"Error: {error.message}")
            if self.verbose and error.details:
                self.print_error(f"Details: {error.details}")
        else:
            self.print_error(f"Unexpected error: {error}")
        raise typer.Exit(1) from None

    def is_raw_mode(self) -> bool:
        """Check if we're in raw output mode."""
        return self.mode == OutputMode.RAW

    def should_suppress_colors(self) -> bool:
        """Check if colors should be suppressed."""
        return self.mode in [OutputMode.RAW, OutputMode.NO_COLOR]
