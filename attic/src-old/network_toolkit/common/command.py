# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Base command infrastructure with unified options and output handling."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypeVar

import typer

from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputMode,
    get_output_manager,
    set_output_mode,
)
from network_toolkit.config import load_config

T = TypeVar("T")

# Common CLI options that should be available across all commands
CommonOptions = dict[str, Any]


def common_options(
    config_file: Annotated[
        Path,
        typer.Option("--config", "-c", help="Configuration file path"),
    ] = Path("devices.yml"),
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    output_mode: Annotated[
        OutputMode | None,
        typer.Option(
            "--output-mode",
            "-o",
            help="Output decoration mode: default, light, dark, no-color, raw",
            show_default=False,
        ),
    ] = None,
) -> CommonOptions:
    """Standard options available to all commands."""
    return {
        "config_file": config_file,
        "verbose": verbose,
        "output_mode": output_mode,
    }


class CommandContext:
    """Unified command execution context with standardized setup."""

    def __init__(
        self,
        config_file: Path,
        verbose: bool = False,
        output_mode: OutputMode | None = None,
    ) -> None:
        """Initialize command context with common setup."""
        # Set up output mode first (before logging)
        if output_mode is not None:
            set_output_mode(output_mode)

        # Set up logging
        setup_logging("DEBUG" if verbose else "INFO")

        # Load configuration
        self.config = load_config(config_file)

        # Get output manager
        self.output = get_output_manager()
        self.console = self.output.console

        # Store options for reference
        self.verbose = verbose
        self.output_mode = output_mode or self.output.mode

    def print_success(self, message: str, context: str | None = None) -> None:
        """Print success message using unified output."""
        self.output.print_success(message, context)

    def print_error(self, message: str, context: str | None = None) -> None:
        """Print error message using unified output."""
        self.output.print_error(message, context)

    def print_warning(self, message: str, context: str | None = None) -> None:
        """Print warning message using unified output."""
        self.output.print_warning(message, context)

    def print_info(self, message: str, context: str | None = None) -> None:
        """Print info message using unified output."""
        self.output.print_info(message, context)

    def print_device_info(self, device: str, message: str) -> None:
        """Print device-specific information."""
        self.output.print_device_info(device, message)

    def print_command_output(self, device: str, command: str, output: str) -> None:
        """Print command execution output."""
        self.output.print_command_output(device, command, output)


# Standard error handling decorator
def handle_toolkit_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle NetworkToolkitError consistently."""

    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            from network_toolkit.exceptions import NetworkToolkitError

            output = get_output_manager()
            if isinstance(e, NetworkToolkitError):
                output.print_error(f"Error: {e.message}")
                if hasattr(e, "details") and e.details:
                    output.print_error(f"Details: {e.details}")
            else:
                output.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from e

    return wrapper


def create_command_context(**options: Any) -> CommandContext:
    """Create a command context from common options."""
    return CommandContext(
        config_file=options.get("config_file", Path("devices.yml")),
        verbose=options.get("verbose", False),
        output_mode=options.get("output_mode"),
    )
