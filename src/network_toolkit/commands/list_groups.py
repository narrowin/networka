# SPDX-License-Identifier: MIT
"""`nw list-groups` command implementation."""

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
    @app.command("list-groups", rich_help_panel="Info & Configuration")
    def list_groups(
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
            bool, typer.Option("--verbose", "-v", help="Show detailed information")
        ] = False,
    ) -> None:
        """List all configured device groups and their members."""
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
                if not config.device_groups:
                    return

                for name, group in config.device_groups.items():
                    # Use the proven get_group_members method
                    group_members = config.get_group_members(name)

                    members_str = ",".join(group_members) if group_members else "none"
                    tags_str = (
                        ",".join(group.match_tags or []) if group.match_tags else "none"
                    )
                    description = group.description or ""
                    print(
                        f"group={name} description={description} tags={tags_str} members={members_str}"
                    )
                return

            # Get the themed console from style manager
            themed_console = style_manager.console

            themed_console.print(
                style_manager.format_message("Device Groups", StyleName.BOLD)
            )
            themed_console.print()

            if not config.device_groups:
                themed_console.print(
                    style_manager.format_message(
                        "No device groups configured", StyleName.WARNING
                    )
                )
                return

            # Create table with centralized styling
            table = style_manager.create_table()
            style_manager.add_column(table, "Group Name", StyleName.DEVICE)
            style_manager.add_column(table, "Description", StyleName.OUTPUT)
            style_manager.add_column(table, "Match Tags", StyleName.COMMAND)
            style_manager.add_column(table, "Members", StyleName.SUCCESS)

            for name, group in config.device_groups.items():
                # Use the proven get_group_members method
                members = config.get_group_members(name)

                table.add_row(
                    name,
                    group.description,
                    ", ".join(group.match_tags) if group.match_tags else "N/A",
                    ", ".join(members) if members else "None",
                )

            themed_console.print(table)
            themed_console.print(
                f"\n{style_manager.format_message(f'Total groups: {len(config.device_groups)}', StyleName.BOLD)}"
            )

            if verbose:
                themed_console.print(
                    f"\n{style_manager.format_message('Usage Examples:', StyleName.BOLD)}"
                )
                for group_name in config.device_groups.keys():
                    themed_console.print(f"  nw group-run {group_name} health_check")

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
