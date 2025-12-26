# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Platform information commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from network_toolkit.api.platforms import (
    PlatformFilterError,
    PlatformListOptions,
    get_platform_details,
    list_platforms,
)
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.platforms.registry import PlatformStatus


def register(app: typer.Typer) -> None:
    """Register the platforms command and its subcommands."""
    platforms_app = typer.Typer(
        name="platforms",
        help="Show platform and vendor support information",
        no_args_is_help=True,
    )

    @platforms_app.command("list")
    def list_platforms_cmd(
        status: Annotated[
            str | None,
            typer.Option(
                "--status",
                "-s",
                help="Filter by status: implemented, planned, sequences_only, experimental",
            ),
        ] = None,
        vendor: Annotated[
            str | None,
            typer.Option(
                "--vendor",
                "-v",
                help="Filter by vendor name (e.g., cisco, mikrotik, arista)",
            ),
        ] = None,
        capability: Annotated[
            str | None,
            typer.Option(
                "--capability",
                "-c",
                help="Filter by capability: config_backup, firmware_upgrade, comprehensive_backup",
            ),
        ] = None,
    ) -> None:
        """List all supported network platforms."""
        ctx = CommandContext()

        options = PlatformListOptions(
            status=status,
            vendor=vendor,
            capability=capability,
        )

        try:
            result = list_platforms(options)
        except PlatformFilterError as e:
            ctx.print_error(e.message)
            raise typer.Exit(1) from None

        if not result.platforms:
            ctx.print_warning("No platforms match the specified filters")
            raise typer.Exit(0)

        # Create Rich table
        table = Table(title="Network Platforms", show_header=True, header_style="bold")
        table.add_column("Platform", style="cyan", no_wrap=True)
        table.add_column("Vendor", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Config Backup", justify="center")
        table.add_column("Firmware", justify="center")
        table.add_column("Comprehensive", justify="center")

        # Status indicators with color
        status_map = {
            PlatformStatus.IMPLEMENTED: "[green]Implemented[/green]",
            PlatformStatus.PLANNED: "[yellow]Planned[/yellow]",
            PlatformStatus.SEQUENCES_ONLY: "[blue]Sequences Only[/blue]",
            PlatformStatus.EXPERIMENTAL: "[magenta]Experimental[/magenta]",
        }

        for platform in result.platforms:
            capability_check = (
                "[green]\u2713[/green]"
                if platform.config_backup
                else "[dim]\u2014[/dim]"
            )
            firmware_check = (
                "[green]\u2713[/green]"
                if platform.firmware_upgrade
                else "[dim]\u2014[/dim]"
            )
            comprehensive_check = (
                "[green]\u2713[/green]"
                if platform.comprehensive_backup
                else "[dim]\u2014[/dim]"
            )

            table.add_row(
                platform.device_type,
                platform.vendor,
                status_map[platform.status],
                capability_check,
                firmware_check,
                comprehensive_check,
            )

        ctx.console.print(table)

    @platforms_app.command("info")
    def platform_info_cmd(
        platform: Annotated[
            str,
            typer.Argument(
                help="Platform device type (e.g., mikrotik_routeros, cisco_ios)"
            ),
        ],
    ) -> None:
        """Show detailed information about a specific platform."""
        ctx = CommandContext()

        details = get_platform_details(platform)
        if details is None:
            ctx.print_error(f"Platform not found: {platform}")
            ctx.print_info("Run 'nw platforms list' to see available platforms")
            raise typer.Exit(1)

        # Status with color
        status_map = {
            PlatformStatus.IMPLEMENTED: "[green]Implemented[/green]",
            PlatformStatus.PLANNED: "[yellow]Planned[/yellow]",
            PlatformStatus.SEQUENCES_ONLY: "[blue]Sequences Only[/blue]",
            PlatformStatus.EXPERIMENTAL: "[magenta]Experimental[/magenta]",
        }

        # Display platform information
        ctx.console.print(f"\n[bold cyan]{platform}[/bold cyan]")
        ctx.console.print(f"Display Name: [bold]{details.display_name}[/bold]")
        ctx.console.print(f"Vendor: [green]{details.vendor}[/green]")
        ctx.console.print(f"Description: {details.description}")
        ctx.console.print(f"Status: {status_map[details.status]}")

        # Operations class
        if details.operations_class:
            ctx.console.print(
                f"\nOperations Class: [dim]{details.operations_class}[/dim]"
            )
        else:
            ctx.console.print("\nOperations Class: [dim]Not configured[/dim]")

        # File extensions
        if details.firmware_extensions:
            ctx.console.print(
                f"Firmware Extensions: {', '.join(details.firmware_extensions)}"
            )

        # Capabilities
        ctx.console.print("\n[bold]Capabilities:[/bold]")

        def cap_symbol(x: bool) -> str:
            return "[green]\u2713[/green]" if x else "[dim]\u2014[/dim]"

        caps = details.capabilities
        ctx.console.print(f"  Config Backup: {cap_symbol(caps.config_backup)}")
        ctx.console.print(f"  Firmware Upgrade: {cap_symbol(caps.firmware_upgrade)}")
        ctx.console.print(
            f"  Firmware Downgrade: {cap_symbol(caps.firmware_downgrade)}"
        )
        ctx.console.print(f"  BIOS Upgrade: {cap_symbol(caps.bios_upgrade)}")
        ctx.console.print(
            f"  Comprehensive Backup: {cap_symbol(caps.comprehensive_backup)}"
        )

        # Documentation
        if details.docs_path:
            ctx.console.print(f"\n[bold]Documentation:[/bold] {details.docs_path}")

        ctx.console.print()  # Empty line at end

    app.add_typer(platforms_app, rich_help_panel="Info & Configuration")


__all__ = ["register"]
