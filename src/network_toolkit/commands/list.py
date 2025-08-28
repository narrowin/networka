# SPDX-License-Identifier: MIT
"""`nw list` command implementation with subcommands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.command_base import standardized_command
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.table_providers import (
    DeviceListTableProvider,
    GlobalSequencesTableProvider,
    GroupListTableProvider,
    SupportedPlatformsTableProvider,
    TransportTypesTableProvider,
    VendorSequencesTableProvider,
)
from network_toolkit.config import NetworkConfig
from network_toolkit.sequence_manager import SequenceManager, SequenceRecord

if TYPE_CHECKING:
    pass


def _list_devices_impl(
    config: NetworkConfig, ctx: CommandContext, *, verbose: bool
) -> None:
    """Implementation logic for listing devices."""
    if not config.devices:
        ctx.print_warning("No devices configured")
        return

    provider = DeviceListTableProvider(config=config)
    ctx.render_table(provider, verbose)


def _list_groups_impl(
    config: NetworkConfig, ctx: CommandContext, *, verbose: bool
) -> None:
    """Implementation logic for listing groups."""
    if not config.device_groups:
        ctx.print_warning("No device groups configured")
        return

    provider = GroupListTableProvider(config=config)
    ctx.render_table(provider, verbose)


def _list_vendor_sequences_impl(
    vendor: str,
    sequences: dict[str, SequenceRecord],
    category_filter: str | None,
    config: NetworkConfig,
    ctx: CommandContext,
    *,
    verbose: bool = False,
) -> None:
    """Implementation logic for listing vendor sequences."""
    if not sequences:
        ctx.print_warning(f"No sequences found for vendor '{vendor}'.")
        return

    filtered_sequences = {
        name: seq
        for name, seq in sequences.items()
        if category_filter is None or seq.category == category_filter
    }

    if not filtered_sequences:
        ctx.print_warning(f"No sequences found for category '{category_filter}'.")
        return

    provider = VendorSequencesTableProvider(
        config=config, vendor_filter=vendor, verbose=verbose
    )
    ctx.render_table(provider, verbose)


def _show_all_vendor_sequences(
    sequences: dict[str, dict[str, SequenceRecord]],
    category_filter: str | None,
    config: NetworkConfig,
    ctx: CommandContext,
    *,
    verbose: bool = False,
) -> None:
    """Show sequences for all vendors."""
    provider = VendorSequencesTableProvider(config=config, verbose=verbose)
    ctx.render_table(provider, verbose)


def _show_global_sequences(
    config: NetworkConfig,
    ctx: CommandContext,
    *,
    verbose: bool = False,
) -> None:
    """Display global sequences."""
    provider = GlobalSequencesTableProvider(config=config, verbose=verbose)
    ctx.render_table(provider, verbose)


def _show_supported_types_impl(ctx: CommandContext, *, verbose: bool) -> None:
    """Implementation logic for showing supported device types."""
    # Show transport types first
    transport_provider = TransportTypesTableProvider()
    ctx.render_table(transport_provider, verbose=False)

    ctx.output_manager.print_blank_line()

    # Show supported device types
    platforms_provider = SupportedPlatformsTableProvider()
    ctx.render_table(platforms_provider, verbose)


def _list_sequences_impl(
    config: NetworkConfig,
    ctx: CommandContext,
    vendor: str | None,
    category: str | None,
    *,
    verbose: bool,
) -> None:
    """Implementation logic for listing sequences."""
    sm = SequenceManager(config)

    # Vendor sequences (built-in + repo + user + config)
    if vendor:
        vendor_seqs = sm.list_vendor_sequences(vendor)
        _list_vendor_sequences_impl(
            vendor, vendor_seqs, category, config, ctx, verbose=verbose
        )
    else:
        all_vendor = sm.list_all_sequences()
        if all_vendor:
            _show_all_vendor_sequences(
                all_vendor, category, config, ctx, verbose=verbose
            )
        else:
            ctx.print_warning("No vendor-specific sequences found.")

    # Show global sequences
    if config.global_command_sequences:
        ctx.output_manager.print_blank_line()
        _show_global_sequences(config, ctx, verbose=verbose)
    else:
        ctx.print_warning("No global sequences found.")


def register(app: typer.Typer) -> None:
    """Register the list command group with the Typer app."""

    # Create the list subcommand group
    list_app = typer.Typer(
        name="list",
        help="List network devices, groups, sequences, and platform information",
    )

    @list_app.command("devices")
    @standardized_command()
    def devices(ctx: CommandContext) -> None:
        """List all configured network devices."""
        config = ctx.config

        if not config.devices:
            ctx.print_warning("No devices configured.")
            return

        # Use the local implementation
        _list_devices_impl(config, ctx, verbose=ctx.verbose)

    @list_app.command("groups")
    @standardized_command()
    def groups(ctx: CommandContext) -> None:
        """List all configured device groups and their members."""
        config = ctx.config

        if not config.device_groups:
            ctx.print_warning("No device groups configured.")
            return

        # Use the local implementation
        _list_groups_impl(config, ctx, verbose=ctx.verbose)

    @list_app.command("sequences")
    @standardized_command()
    def sequences(
        ctx: CommandContext,
        vendor: Annotated[
            str | None,
            typer.Option("--vendor", "-v", help="Filter by vendor platform"),
        ] = None,
        category: Annotated[
            str | None,
            typer.Option("--category", help="Filter by sequence category"),
        ] = None,
    ) -> None:
        """List all available command sequences, optionally filtered by vendor
        or category."""
        config = ctx.config

        # Use the local implementation
        _list_sequences_impl(config, ctx, vendor, category, verbose=ctx.verbose)

    @list_app.command("supported-types")
    @standardized_command(has_config=False)
    def supported_types(ctx: CommandContext) -> None:
        """Show supported device types and platform information."""
        # Use the local implementation
        _show_supported_types_impl(ctx, verbose=ctx.verbose)

    # Register the list command group with the main app
    app.add_typer(list_app, name="list", rich_help_panel="Info & Configuration")
