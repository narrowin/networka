# SPDX-License-Identifier: MIT
"""`nw config-validate` command implementation."""

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
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command("config-validate", rich_help_panel="Info & Configuration")
    def config_validate(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose", "-v", help="Show detailed validation information"
            ),
        ] = False,
    ) -> None:
        """Validate the configuration file and show any issues."""
        setup_logging("DEBUG" if verbose else "INFO")

        output_manager = None
        try:
            config = load_config(config_file)

            # Handle output mode configuration
            if output_mode is not None:
                set_output_mode(output_mode)
                output_manager = get_output_manager()
            else:
                # Use config-based output mode
                output_manager = get_output_manager_with_config(
                    config.general.output_mode
                )

            output_manager.print_info(f"Validating Configuration: {config_file}")
            output_manager.print_blank_line()

            output_manager.print_success("Configuration is valid!")
            output_manager.print_blank_line()

            device_count = len(config.devices) if config.devices else 0
            group_count = len(config.device_groups) if config.device_groups else 0
            global_seq_count = (
                len(config.global_command_sequences)
                if config.global_command_sequences
                else 0
            )

            output_manager.print_info(f"Devices: {device_count}")
            output_manager.print_info(f"Device Groups: {group_count}")
            output_manager.print_info(f"Global Sequences: {global_seq_count}")

            if verbose and device_count > 0 and config.devices:
                output_manager.print_blank_line()
                output_manager.print_info("Device Summary:")
                for name, device in config.devices.items():
                    output_manager.print_info(
                        f"  • {name} ({device.host}) - {device.device_type}"
                    )

        except NetworkToolkitError as e:
            # Initialize output_manager if not already set
            if output_manager is None:
                output_manager = get_output_manager()
            output_manager.print_error("Configuration validation failed!")
            output_manager.print_error(f"Error: {e.message}")
            if verbose and e.details:
                output_manager.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            # Initialize output_manager if not already set
            if output_manager is None:
                output_manager = get_output_manager()
            output_manager.print_error(f"Unexpected error during validation: {e}")
            raise typer.Exit(1) from None


def _config_validate_impl(
    config_file: Path,
    output_mode: OutputMode | None = None,
    verbose: bool = False,
) -> None:
    """Implementation function for config validate that can be called from unified command.

    This delegates to the original config_validate function by creating a temporary Typer app
    and calling the registered command.
    """
    # Create a temporary app to get access to the registered command
    temp_app = typer.Typer()
    register(temp_app)

    # Find and call the registered command function
    for cmd_info in temp_app.registered_commands:
        if cmd_info.name == "config-validate" and cmd_info.callback:
            cmd_info.callback(
                config_file=config_file,
                output_mode=output_mode,
                verbose=verbose,
            )
            return

    # This should never happen
    error_msg = "Could not find config-validate command in registered commands"
    raise RuntimeError(error_msg)
