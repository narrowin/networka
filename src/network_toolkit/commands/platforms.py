# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Platform information commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from network_toolkit.api.platforms import (
    PlatformDetails,
    PlatformFilterError,
    PlatformListOptions,
    get_platform_details,
    list_platforms,
)
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.config import NetworkConfig, load_inspection_config
from network_toolkit.exceptions import ConfigurationError
from network_toolkit.platforms.registry import PlatformStatus
from network_toolkit.sequence_manager import SequenceManager
from network_toolkit.transport.scrapli_sync import (
    SCRAPLI_PLATFORM_ALIASES,
    get_scrapli_definition_catalog,
)

_STATUS_LABELS = {
    PlatformStatus.IMPLEMENTED: "[green]Implemented[/green]",
    PlatformStatus.PLANNED: "[yellow]Planned[/yellow]",
    PlatformStatus.SEQUENCES_ONLY: "[blue]Sequences Only[/blue]",
    PlatformStatus.EXPERIMENTAL: "[magenta]Experimental[/magenta]",
}


def _catalog_source(override: Path | None, name: str | None = None) -> str:
    path = override if override is not None else Path("scrapli.definitions")
    if name is not None:
        path /= f"{name}.yaml"
    label = "SCRAPLI_DEFINITIONS_PATH" if override is not None else "Packaged Scrapli"
    return f"{label} ({path})"


def _print_registered_operations(ctx: CommandContext, details: PlatformDetails) -> None:
    ctx.console.print(f"Display Name: [bold]{details.display_name}[/bold]")
    ctx.console.print(f"Vendor: [green]{details.vendor}[/green]")
    ctx.console.print(f"Description: {details.description}")
    ctx.console.print(f"Registry Status: {_STATUS_LABELS[details.status]}")
    ctx.console.print(
        f"Operations Class: [dim]{details.operations_class or 'Not configured'}[/dim]"
    )
    if details.firmware_extensions:
        ctx.console.print(
            f"Firmware Extensions: {', '.join(details.firmware_extensions)}"
        )

    ctx.console.print("\n[bold]Vendor operation capabilities[/bold]")
    caps = details.capabilities
    for label, enabled in (
        ("Config Backup", caps.config_backup),
        ("Firmware Upgrade", caps.firmware_upgrade),
        ("Firmware Downgrade", caps.firmware_downgrade),
        ("BIOS Upgrade", caps.bios_upgrade),
        ("Comprehensive Backup", caps.comprehensive_backup),
    ):
        symbol = "[green]✓[/green]" if enabled else "[dim]—[/dim]"
        ctx.console.print(f"  {label}: {symbol}")
    if details.docs_path:
        ctx.console.print(f"\n[bold]Documentation:[/bold] {details.docs_path}")


def _print_platform_sequences(
    ctx: CommandContext, config: NetworkConfig, platform: str
) -> None:
    records = SequenceManager(config).list_platform_sequences(platform)
    if not records:
        ctx.console.print("\nPlatform sequences: None")
        return

    ctx.console.print("\n[bold]Platform sequences and sources[/bold]")
    for name, record in sorted(records.items()):
        if record.source is None:
            origin = "source unavailable"
        else:
            origin = (
                "packaged"
                if record.source.origin == "builtin"
                else record.source.origin
            )
            if record.source.path is not None:
                origin = f"{origin}: {record.source.path}"
        ctx.console.print(
            f"  {name} ({origin})", markup=False, highlight=False, soft_wrap=True
        )

    ctx.console.print(
        f"Inspect commands with nw info <sequence> --vendor {platform}",
        markup=False,
        highlight=False,
    )


def register(app: typer.Typer) -> None:
    """Register the platforms command and its subcommands."""
    platforms_app = typer.Typer(
        name="platforms",
        help="Inspect Scrapli definitions and registered platform support",
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
        """List active Scrapli definitions and registered network platforms."""
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
        table = Table(
            title="Network Platforms (registry)", show_header=True, header_style="bold"
        )
        table.add_column("Platform", style="cyan", no_wrap=True)
        table.add_column("Vendor", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Config Backup", justify="center")
        table.add_column("Firmware", justify="center")
        table.add_column("Comprehensive", justify="center")

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
                _STATUS_LABELS[platform.status],
                capability_check,
                firmware_check,
                comprehensive_check,
            )

        ctx.console.print(table)

        if status is None and vendor is None and capability is None:
            definitions, override = get_scrapli_definition_catalog()
            ctx.console.print("\n[bold]Active Scrapli definitions[/bold]")
            ctx.console.print(
                f"Source: {_catalog_source(override)}",
                markup=False,
                highlight=False,
                soft_wrap=True,
            )
            ctx.console.print(
                ", ".join(sorted(definitions)) or "No definition files found.",
                markup=False,
                highlight=False,
            )

    @platforms_app.command("info")
    def platform_info_cmd(
        platform: Annotated[
            str,
            typer.Argument(
                help="Platform or definition name (e.g., mikrotik_routeros, cumulus_linux)"
            ),
        ],
    ) -> None:
        """Show the connection definition, vendor operations, and platform sequences."""
        try:
            config = load_inspection_config(None)
        except (ConfigurationError, OSError, ValueError) as exc:
            CommandContext(config=NetworkConfig()).print_error(str(exc))
            raise typer.Exit(1) from None
        ctx = CommandContext(config=config)

        details = get_platform_details(platform)
        definitions, override = get_scrapli_definition_catalog()
        definition = SCRAPLI_PLATFORM_ALIASES.get(platform, platform) or "default"
        available = definition in definitions
        if details is None and not available:
            ctx.print_error(f"Platform not found: {platform}")
            ctx.print_info("Run 'nw platforms list' to see active definitions")
            raise typer.Exit(1)

        ctx.console.print(f"\n{platform}", style="bold cyan", markup=False)
        if definition != platform:
            ctx.console.print(f"Scrapli alias: {platform} → {definition}", markup=False)
        status = definition if available else f"{definition} (unavailable)"
        ctx.console.print(f"Scrapli definition: {status}", markup=False)
        source = _catalog_source(override, definition if available else None)
        ctx.console.print(
            f"Definition source: {source}",
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
        if not available:
            ctx.print_info("Run 'nw platforms list' to see active definitions")

        if details is None:
            ctx.console.print("Registered vendor operations: None")
        else:
            _print_registered_operations(ctx, details)
        _print_platform_sequences(ctx, config, platform)

    app.add_typer(platforms_app, rich_help_panel="Info & Configuration")


__all__ = ["register"]
