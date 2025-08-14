# SPDX-License-Identifier: MIT
"""`nw list-groups` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.common.output import (
    OutputMode,
    get_output_manager,
    set_output_mode,
)
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command("list-groups", rich_help_panel="Info & Configuration")
    def list_groups(
        config_file: Annotated[Path, typer.Option("--config", "-c", help="Configuration file path")] = Path(
            "devices.yml"
        ),
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed information")] = False,
    ) -> None:
        """List all configured device groups and their members."""
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            config = load_config(config_file)

            # Handle output mode configuration
            if output_mode is not None:
                set_output_mode(output_mode)
                output_manager = get_output_manager()
            else:
                # Use config-based output mode
                from network_toolkit.common.output import get_output_manager_with_config
                output_manager = get_output_manager_with_config(config.general.output_mode)

            if output_manager.mode == OutputMode.RAW:
                # Raw mode output
                if not config.device_groups:
                    return

                for name, group in config.device_groups.items():
                    group_members: list[str] = []
                    if group.members:
                        group_members = group.members
                    elif group.match_tags and config.devices:
                        # Find devices matching tags
                        for device_name, device_config in config.devices.items():
                            if device_config.tags and any(tag in group.match_tags for tag in device_config.tags):
                                group_members.append(device_name)

                    members_str = ",".join(group_members) if group_members else "none"
                    tags_str = ",".join(group.match_tags or []) if group.match_tags else "none"
                    description = group.description or ""
                    print(f"group={name} description={description} tags={tags_str} members={members_str}")
                return

            # Get the themed console from output manager
            themed_console = output_manager.console

            themed_console.print("[bold]Device Groups[/bold]")
            themed_console.print()

            if not config.device_groups:
                themed_console.print("[warning]No device groups configured[/warning]")
                return

            table = Table()
            table.add_column("Group Name", style="device")  # Use theme color
            table.add_column("Description", style="output")  # Use theme color
            table.add_column("Match Tags", style="command")  # Use theme color
            table.add_column("Members", style="success")  # Use theme color

            for name, group in config.device_groups.items():
                members: list[str] = []
                if group.members:
                    members = group.members
                elif group.match_tags and config.devices:
                    for device_name, device_config in config.devices.items():
                        if device_config.tags and any(tag in device_config.tags for tag in group.match_tags):
                            members.append(device_name)

                table.add_row(
                    name,
                    group.description,
                    ", ".join(group.match_tags) if group.match_tags else "N/A",
                    ", ".join(members) if members else "None",
                )

            themed_console.print(table)
            themed_console.print(f"\n[bold]Total groups: {len(config.device_groups)}[/bold]")

            if verbose:
                themed_console.print("\n[bold success]Usage Examples:[/bold success]")
                for group_name in config.device_groups.keys():
                    themed_console.print(f"  nw group-run {group_name} health_check")

        except NetworkToolkitError as e:
            output_manager.print_error(f"Error: {e.message}")
            if verbose and e.details:
                output_manager.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            output_manager.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
