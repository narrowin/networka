# SPDX-License-Identifier: MIT
"""Helper utilities for consistent command styling and output."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputMode,
    get_output_manager,
    set_output_mode,
)
from network_toolkit.common.styles import StyleManager, StyleName
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from network_toolkit.common.table_generator import TableDataProvider, TableGenerator


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

        config = None
        if self.config_file and self.config_file.exists():
            try:
                config = load_config(self.config_file)
            except Exception:
                config = None

        active_output_mode = output_mode
        if active_output_mode is None and config is not None:
            active_output_mode = OutputMode(config.general.output_mode)

        if active_output_mode is not None:
            set_output_mode(active_output_mode)

        if verbose:
            logging.disable(logging.NOTSET)
            setup_logging("DEBUG")
        elif config is not None and not config.general.enable_logging:
            setup_logging("CRITICAL")
            logging.disable(logging.CRITICAL)
        else:
            logging.disable(logging.NOTSET)
            effective_level = (
                config.general.log_level if config is not None else "WARNING"
            )
            setup_logging(effective_level)

        self.output_manager = get_output_manager()
        if active_output_mode is None:
            active_output_mode = self.output_manager.mode

        self.config = config
        self.output_mode = active_output_mode

        # Create style manager for themed output
        self.style_manager = StyleManager(self.output_manager.mode)

        # Expose commonly used objects
        self.console = self.style_manager.console
        self.mode = self.output_manager.mode

    @property
    def table_generator(self) -> TableGenerator:
        """Get table generator for this context."""
        if not hasattr(self, "_table_generator"):
            from network_toolkit.common.table_generator import TableGenerator

            self._table_generator = TableGenerator(
                self.style_manager, self.output_manager
            )
        return self._table_generator

    def render_table(self, provider: TableDataProvider, verbose: bool = False) -> None:
        """Convenience method to render a table."""
        self.table_generator.render_table(provider, verbose)

    def print_error(self, message: str, device_name: str | None = None) -> None:
        """Print an error message with proper styling."""
        self.output_manager.print_error(message, device_name)

    def print_warning(self, message: str, device_name: str | None = None) -> None:
        """Print a warning message with proper styling."""
        self.output_manager.print_warning(message, device_name)

    def print_success(self, message: str, device_name: str | None = None) -> None:
        """Print a success message with proper styling."""
        self.output_manager.print_success(message, device_name)

    def print_info(self, message: str, device_name: str | None = None) -> None:
        """Print an info message with proper styling."""
        self.output_manager.print_info(message, device_name)

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

    def print_operation_header(
        self, operation: str, target: str, target_type: str = "device"
    ) -> None:
        """Print operation start header with consistent formatting."""
        if self.mode == OutputMode.RAW:
            self.output_manager.print_info(
                f"operation={operation} {target_type}={target}"
            )
        else:
            # Use style manager to format the message properly
            formatted_msg = self.style_manager.format_message(
                f"{operation}: {target}", StyleName.INFO
            )
            # Make it bold for emphasis
            formatted_msg = self.style_manager.format_message(
                formatted_msg, StyleName.BOLD
            )
            self.output_manager.print_text(formatted_msg)

    def print_operation_complete(self, operation: str, success: bool = True) -> None:
        """Print operation completion status with consistent formatting."""
        if success:
            if self.mode == OutputMode.RAW:
                self.output_manager.print_info("status=completed")
            else:
                # Use semantic success method
                self.output_manager.print_success(f"{operation} completed successfully")
        elif self.mode == OutputMode.RAW:
            self.output_manager.print_info("status=failed")
        else:
            # Use semantic error method
            self.output_manager.print_error(f"{operation} failed")

    def print_detail_line(self, label: str, value: str) -> None:
        """Print a detail line with consistent formatting."""
        if self.mode == OutputMode.RAW:
            key = label.lower().replace(" ", "_").replace(":", "")
            self.output_manager.print_info(f"{key}={value}")
        else:
            # Use style manager for dim/subtle formatting
            formatted_msg = self.style_manager.format_message(
                f"  {label}: {value}", StyleName.DIM
            )
            self.output_manager.print_text(formatted_msg)

    def print_usage_examples_header(self) -> None:
        """Print usage examples section header."""
        if self.mode == OutputMode.RAW:
            self.output_manager.print_info("section=usage_examples")
        else:
            # Use style manager for warning color (yellow) and bold
            formatted_msg = self.style_manager.format_message(
                "\nUsage Examples:", StyleName.WARNING
            )
            formatted_msg = self.style_manager.format_message(
                formatted_msg, StyleName.BOLD
            )
            self.output_manager.print_text(formatted_msg)

    def print_separator(self) -> None:
        """Print a separator line."""
        self.output_manager.print_separator()

    def print_blank_line(self) -> None:
        """Print a blank line."""
        self.output_manager.print_blank_line()

    def print_code_block(self, text: str) -> None:
        """Print a code block or configuration text."""
        if self.mode == OutputMode.RAW:
            # In raw mode, just print the text as-is
            self.output_manager.print_output(text)
        else:
            # In styled modes, preserve any existing formatting
            self.output_manager.print_text(text)
