# SPDX-License-Identifier: MIT
"""`nw list-devices` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

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


def register(app: typer.Typer) -> None:
    @app.command("list-devices", rich_help_panel="Info & Configuration")
    def list_devices(
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
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
    ) -> None:
        """List all configured network devices."""
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
                from network_toolkit.common.output import get_output_manager_with_config

                output_manager = get_output_manager_with_config(
                    config.general.output_mode
                )

            # Create style manager for consistent theming
            style_manager = StyleManager(output_manager.mode)

            if output_manager.mode == OutputMode.RAW:
                # Raw mode output
                if not config.devices:
                    return

                for name, device in config.devices.items():
                    tags_str = ",".join(device.tags or []) if device.tags else "none"
                    platform = device.platform or "unknown"
                    print(
                        f"device={name} host={device.host} platform={platform} tags={tags_str}"
                    )
                return

            # Get the themed console from style manager
            themed_console = style_manager.console

            themed_console.print(
                style_manager.format_message("Configured Devices", StyleName.BOLD)
            )
            themed_console.print()

            if not config.devices:
                themed_console.print(
                    style_manager.format_message(
                        "No devices configured", StyleName.WARNING
                    )
                )
                return

            # Create table with centralized styling
            table = style_manager.create_table()
            style_manager.add_column(table, "Name", StyleName.DEVICE)
            style_manager.add_column(table, "Host", StyleName.HOST)
            style_manager.add_column(table, "Type", StyleName.PLATFORM)
            style_manager.add_column(table, "Description", StyleName.OUTPUT)
            style_manager.add_column(table, "Tags", StyleName.SUCCESS)

            for name, device_config in config.devices.items():
                table.add_row(
                    name,
                    device_config.host,
                    device_config.device_type,
                    device_config.description or "N/A",
                    ", ".join(device_config.tags) if device_config.tags else "None",
                )

            themed_console.print(table)
            themed_console.print(
                f"\n{style_manager.format_message(f'Total devices: {len(config.devices)}', StyleName.BOLD)}"
            )

        except NetworkToolkitError as e:
            # Initialize output_manager if not already set
            if output_manager is None:
                output_manager = get_output_manager()
            output_manager.print_error(f"Error: {e.message}")
            if verbose and e.details:
                output_manager.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            # Initialize output_manager if not already set
            if output_manager is None:
                output_manager = get_output_manager()
            output_manager.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
