# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Platform information commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.platforms.registry import (
    PLATFORM_REGISTRY,
    PlatformInfo,
    PlatformStatus,
    get_platforms_by_status,
    get_platforms_by_vendor,
    get_platforms_with_capability,
)


def register(app: typer.Typer) -> None:
    """Register the platforms command and its subcommands."""
    platforms_app = typer.Typer(
        name="platforms",
        help="Show platform and vendor support information",
        no_args_is_help=True,
    )

    @platforms_app.command("list")
    def list_platforms(
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

        # Build platform dictionary based on filters
        platform_dict: dict[str, PlatformInfo]

        if status:
            try:
                # Enum values are lowercase, but accept either case from user
                status_lower = status.lower()
                status_enum = PlatformStatus(status_lower)
                platform_dict = get_platforms_by_status(status_enum)
            except ValueError:
                ctx.print_error(
                    f"Invalid status: {status}. Valid values: implemented, planned, sequences_only, experimental"
                )
                raise typer.Exit(1) from None
        elif vendor:
            platforms = get_platforms_by_vendor(vendor.lower())
            if not platforms:
                ctx.print_error(f"No platforms found for vendor: {vendor}")
                raise typer.Exit(1)
            platform_dict = {p.device_type: p for p in platforms}
        elif capability:
            valid_capabilities = [
                "config_backup",
                "firmware_upgrade",
                "comprehensive_backup",
            ]
            if capability not in valid_capabilities:
                ctx.print_error(
                    f"Invalid capability: {capability}. Valid values: {', '.join(valid_capabilities)}"
                )
                raise typer.Exit(1)
            platforms = get_platforms_with_capability(capability)
            platform_dict = {p.device_type: p for p in platforms}
        else:
            platform_dict = PLATFORM_REGISTRY

        platform_list = list(platform_dict.keys())

        if not platform_list:
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

        # Sort platforms by vendor, then by name
        sorted_platforms = sorted(
            platform_list,
            key=lambda p: (platform_dict[p].vendor, p),
        )

        for platform_name in sorted_platforms:
            info = platform_dict[platform_name]

            # Status indicators with color
            status_map = {
                PlatformStatus.IMPLEMENTED: "[green]Implemented[/green]",
                PlatformStatus.PLANNED: "[yellow]Planned[/yellow]",
                PlatformStatus.SEQUENCES_ONLY: "[blue]Sequences Only[/blue]",
                PlatformStatus.EXPERIMENTAL: "[magenta]Experimental[/magenta]",
            }

            capability_check = (
                "[green]✓[/green]"
                if info.capabilities.config_backup
                else "[dim]—[/dim]"
            )
            firmware_check = (
                "[green]✓[/green]"
                if info.capabilities.firmware_upgrade
                else "[dim]—[/dim]"
            )
            comprehensive_check = (
                "[green]✓[/green]"
                if info.capabilities.comprehensive_backup
                else "[dim]—[/dim]"
            )

            table.add_row(
                platform_name,
                info.vendor,
                status_map[info.status],
                capability_check,
                firmware_check,
                comprehensive_check,
            )

        ctx.console.print(table)

    @platforms_app.command("info")
    def platform_info(
        platform: Annotated[
            str,
            typer.Argument(
                help="Platform device type (e.g., mikrotik_routeros, cisco_ios)"
            ),
        ],
    ) -> None:
        """Show detailed information about a specific platform."""
        ctx = CommandContext()

        if platform not in PLATFORM_REGISTRY:
            ctx.print_error(f"Platform not found: {platform}")
            ctx.print_info("Run 'nw platforms list' to see available platforms")
            raise typer.Exit(1)

        info = PLATFORM_REGISTRY[platform]

        # Status with color
        status_map = {
            PlatformStatus.IMPLEMENTED: "[green]Implemented[/green]",
            PlatformStatus.PLANNED: "[yellow]Planned[/yellow]",
            PlatformStatus.SEQUENCES_ONLY: "[blue]Sequences Only[/blue]",
            PlatformStatus.EXPERIMENTAL: "[magenta]Experimental[/magenta]",
        }

        # Display platform information
        ctx.console.print(f"\n[bold cyan]{platform}[/bold cyan]")
        ctx.console.print(f"Display Name: [bold]{info.display_name}[/bold]")
        ctx.console.print(f"Vendor: [green]{info.vendor}[/green]")
        ctx.console.print(f"Description: {info.description}")
        ctx.console.print(f"Status: {status_map[info.status]}")

        # Operations class
        if info.operations_class:
            ctx.console.print(f"\nOperations Class: [dim]{info.operations_class}[/dim]")
        else:
            ctx.console.print("\nOperations Class: [dim]Not configured[/dim]")

        # File extensions
        if info.firmware_extensions:
            ctx.console.print(
                f"Firmware Extensions: {', '.join(info.firmware_extensions)}"
            )

        # Capabilities
        ctx.console.print("\n[bold]Capabilities:[/bold]")

        def cap_symbol(x: bool) -> str:
            return "[green]✓[/green]" if x else "[dim]—[/dim]"

        ctx.console.print(
            f"  Config Backup: {cap_symbol(info.capabilities.config_backup)}"
        )
        ctx.console.print(
            f"  Firmware Upgrade: {cap_symbol(info.capabilities.firmware_upgrade)}"
        )
        ctx.console.print(
            f"  Firmware Downgrade: {cap_symbol(info.capabilities.firmware_downgrade)}"
        )
        ctx.console.print(
            f"  BIOS Upgrade: {cap_symbol(info.capabilities.bios_upgrade)}"
        )
        ctx.console.print(
            f"  Comprehensive Backup: {cap_symbol(info.capabilities.comprehensive_backup)}"
        )

        # Documentation
        if info.docs_path:
            ctx.console.print(f"\n[bold]Documentation:[/bold] {info.docs_path}")

        ctx.console.print()  # Empty line at end

    app.add_typer(platforms_app, rich_help_panel="Info & Configuration")


__all__ = ["register"]
