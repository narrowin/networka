# SPDX-License-Identifier: MIT
"""`nw list-groups` command implementation."""

from __future__ import annotations

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
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from network_toolkit.common.command_helpers import CommandContext
    from network_toolkit.config import NetworkConfig


def _list_groups_impl(
    config: NetworkConfig, ctx: CommandContext, verbose: bool
) -> None:
    """Implementation logic for listing groups."""
    from rich.table import Table

    if ctx.output_manager.mode == ctx.output_manager.mode.RAW:
        # Raw mode output
        if not config.device_groups:
            return

        for name, group in config.device_groups.items():
            # Use the proven get_group_members method
            group_members = config.get_group_members(name)

            members_str = ",".join(group_members) if group_members else "none"
            tags_str = ",".join(group.match_tags or []) if group.match_tags else "none"
            description = group.description or ""
            print(
                f"group={name} description={description} tags={tags_str} members={members_str}"
            )
        return

    # Headline
    ctx.print_info("Device Groups")
    ctx.output_manager.print_blank_line()

    if not config.device_groups:
        ctx.print_warning("No device groups configured")
        return

    # Create table with centralized styling
    table = Table(title="Groups", show_header=True, box=None)
    table.add_column("Group Name")
    table.add_column("Description")
    table.add_column("Match Tags")
    table.add_column("Members")

    for name, group in config.device_groups.items():
        # Use the proven get_group_members method
        members = config.get_group_members(name)

        table.add_row(
            name,
            group.description,
            ", ".join(group.match_tags) if group.match_tags else "N/A",
            ", ".join(members) if members else "None",
        )

    ctx.output_manager.console.print(table)
    ctx.output_manager.print_blank_line()
    ctx.print_info(f"Total groups: {len(config.device_groups)}")

    if verbose:
        ctx.output_manager.print_blank_line()
        ctx.print_info("Usage Examples:")
        for group_name in config.device_groups.keys():
            ctx.print_info(f"  nw group-run {group_name} health_check")


def register(app: typer.Typer) -> None:
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

            # Headline
            output_manager.print_info("Device Groups")
            output_manager.print_blank_line()

            if not config.device_groups:
                output_manager.print_warning("No device groups configured")
                return

            # Create table with centralized styling
            table = output_manager.create_table(
                title="Groups", show_header=True, box=None
            )
            table.add_column("Group Name")
            table.add_column("Description")
            table.add_column("Match Tags")
            table.add_column("Members")

            for name, group in config.device_groups.items():
                # Use the proven get_group_members method
                members = config.get_group_members(name)

                table.add_row(
                    name,
                    group.description,
                    ", ".join(group.match_tags) if group.match_tags else "N/A",
                    ", ".join(members) if members else "None",
                )

            output_manager.print_table(table)
            output_manager.print_blank_line()
            output_manager.print_info(f"Total groups: {len(config.device_groups)}")

            if verbose:
                output_manager.print_blank_line()
                output_manager.print_info("Usage Examples:")
                for group_name in config.device_groups.keys():
                    output_manager.print_info(
                        f"  nw group-run {group_name} health_check"
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
