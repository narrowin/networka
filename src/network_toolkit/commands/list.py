# SPDX-License-Identifier: MIT
"""`nw list` command implementation with subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode, get_output_manager
from network_toolkit.common.styles import StyleManager, StyleName
from network_toolkit.common.table_providers import (
    DeviceListTableProvider,
    GroupListTableProvider,
    SupportedPlatformsTableProvider,
    TransportTypesTableProvider,
)
from network_toolkit.config import CommandSequence, NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.sequence_manager import SequenceManager, SequenceRecord

if TYPE_CHECKING:
    from network_toolkit.common.output import OutputManager
    from network_toolkit.config import NetworkConfig


def _list_devices_impl(
    config: NetworkConfig, ctx: CommandContext, verbose: bool
) -> None:
    """Implementation logic for listing devices."""
    if not config.devices:
        ctx.print_warning("No devices configured")
        return

    provider = DeviceListTableProvider(config=config)
    ctx.render_table(provider, verbose)


def _list_groups_impl(
    config: NetworkConfig, ctx: CommandContext, verbose: bool
) -> None:
    """Implementation logic for listing groups."""
    if not config.device_groups:
        ctx.print_warning("No device groups configured")
        return

    provider = GroupListTableProvider(config=config)
    ctx.render_table(provider, verbose)


def _show_vendor_sequences(
    vendor: str,
    sequences: dict[str, SequenceRecord],
    category_filter: str | None,
    style_manager: StyleManager,
    *,
    verbose: bool = False,
) -> None:
    """Show sequences for a specific vendor."""
    output_manager = get_output_manager()
    output_manager.print_text(
        style_manager.format_message(
            f"Command Sequences for {vendor.title()}", StyleName.BOLD
        )
    )

    if not sequences:
        output_manager.print_text(
            style_manager.format_message(
                "No sequences found for this vendor.", StyleName.WARNING
            )
        )
        return

    # Filter by category if specified
    filtered_sequences = sequences
    if category_filter:
        filtered_sequences = {
            name: seq
            for name, seq in sequences.items()
            if hasattr(seq, "category") and seq.category == category_filter
        }

    if not filtered_sequences:
        output_manager.print_text(
            style_manager.format_message(
                f"No sequences found for category '{category_filter}'.",
                StyleName.WARNING,
            )
        )
        return

    table = style_manager.create_table()
    style_manager.add_column(table, "Sequence Name", StyleName.DEVICE)
    style_manager.add_column(table, "Description", StyleName.SUCCESS)
    style_manager.add_column(table, "Category", StyleName.WARNING)
    style_manager.add_column(table, "Commands", StyleName.OUTPUT)

    if verbose:
        style_manager.add_column(table, "Timeout", StyleName.INFO)
        style_manager.add_column(table, "Device Types", StyleName.ERROR)

    preview_limit = 3
    for name, seq in sorted(filtered_sequences.items()):
        commands_str = str(len(seq.commands)) + " commands"
        if verbose and len(seq.commands) <= preview_limit:
            commands_str = ", ".join(seq.commands[:3])
        elif verbose:
            commands_str = (
                f"{', '.join(seq.commands[:2])}, ... (+{len(seq.commands) - 2} more)"
            )

        row = [
            name,
            seq.description or "No description",
            seq.category or "general",
            commands_str,
        ]

        if verbose:
            row.append(str(seq.timeout) if seq.timeout else "default")
            device_types = ", ".join(seq.device_types) if seq.device_types else "all"
            row.append(device_types)

        table.add_row(*row)

    output_manager.print_table(table)


def _show_all_vendor_sequences(
    sequences: dict[str, dict[str, SequenceRecord]],
    category_filter: str | None,
    style_manager: StyleManager,
    *,
    verbose: bool = False,
) -> None:
    """Show sequences for all vendors."""
    output_manager = get_output_manager()
    output_manager.print_text(
        style_manager.format_message("All Vendor Sequences", StyleName.BOLD)
    )

    for vendor, vendor_sequences in sorted(sequences.items()):
        if vendor_sequences:  # Only show vendors that have sequences
            output_manager.print_blank_line()
            _show_vendor_sequences(
                vendor,
                vendor_sequences,
                category_filter,
                style_manager,
                verbose=verbose,
            )


def _show_global_sequences(
    global_sequences: dict[str, CommandSequence],
    style_manager: StyleManager,
    output_manager: OutputManager,
    *,
    verbose: bool = False,
) -> None:
    """Display global sequences."""
    output_manager.print_text(
        style_manager.format_message("Global Sequences", StyleName.BOLD)
    )

    table = style_manager.create_table()
    style_manager.add_column(table, "Sequence Name", StyleName.DEVICE)
    style_manager.add_column(table, "Description", StyleName.SUCCESS)
    style_manager.add_column(table, "Commands", StyleName.OUTPUT)

    if verbose:
        style_manager.add_column(table, "Tags", StyleName.WARNING)

    for name, seq in sorted(global_sequences.items()):
        commands_str = str(len(seq.commands)) + " commands"
        if verbose and len(seq.commands) <= 3:
            commands_str = ", ".join(seq.commands[:3])
        elif verbose:
            commands_str = (
                f"{', '.join(seq.commands[:2])}, ... (+{len(seq.commands) - 2} more)"
            )

        row = [
            name,
            seq.description or "No description",
            commands_str,
        ]

        if verbose:
            tags_str = ", ".join(seq.tags) if seq.tags else "none"
            row.append(tags_str)

        table.add_row(*row)

    output_manager.print_table(table)


def _show_supported_types_impl(ctx: CommandContext, verbose: bool) -> None:
    """Implementation logic for showing supported device types."""
    # Show transport types first
    transport_provider = TransportTypesTableProvider()
    ctx.render_table(transport_provider, False)

    ctx.output_manager.print_blank_line()

    # Show supported device types
    platforms_provider = SupportedPlatformsTableProvider()
    ctx.render_table(platforms_provider, verbose)


def _list_sequences_impl(
    config: NetworkConfig,
    ctx: CommandContext,
    vendor: str | None,
    category: str | None,
    verbose: bool,
) -> None:
    """Implementation logic for listing sequences."""
    sm = SequenceManager(config)

    # Vendor sequences (built-in + repo + user + config)
    if vendor:
        vendor_seqs = sm.list_vendor_sequences(vendor)
        _show_vendor_sequences(
            vendor, vendor_seqs, category, ctx.style_manager, verbose=verbose
        )
    else:
        all_vendor = sm.list_all_sequences()
        if all_vendor:
            _show_all_vendor_sequences(
                all_vendor, category, ctx.style_manager, verbose=verbose
            )
        else:
            ctx.print_warning("No vendor-specific sequences found.")

    # Show global sequences if they exist
    if config.global_command_sequences:
        ctx.output_manager.print_blank_line()
        _show_global_sequences(
            config.global_command_sequences,
            ctx.style_manager,
            ctx.output_manager,
            verbose=verbose,
        )


def register(app: typer.Typer) -> None:
    """Register the list command group with the Typer app."""

    # Create the list subcommand group
    list_app = typer.Typer(
        name="list",
        help="List network devices, groups, sequences, and platform information",
    )

    @list_app.command("devices")
    def devices(
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

        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(config_file)

            if not config.devices:
                ctx.print_warning("No devices configured.")
                return

            # Use the local implementation
            _list_devices_impl(config, ctx, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @list_app.command("groups")
    def groups(
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

        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(config_file)

            if not config.device_groups:
                ctx.print_warning("No device groups configured.")
                return

            # Use the local implementation
            _list_groups_impl(config, ctx, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @list_app.command("sequences")
    def sequences(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        vendor: Annotated[
            str | None,
            typer.Option("--vendor", "-v", help="Filter by vendor platform"),
        ] = None,
        category: Annotated[
            str | None,
            typer.Option("--category", help="Filter by sequence category"),
        ] = None,
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
            bool, typer.Option("--verbose", help="Show detailed information")
        ] = False,
    ) -> None:
        """List all available command sequences, optionally filtered by vendor or category."""
        setup_logging("DEBUG" if verbose else "INFO")

        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(config_file)

            # Use the local implementation
            _list_sequences_impl(config, ctx, vendor, category, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @list_app.command("supported-types")
    def supported_types(
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Show detailed information")
        ] = False,
    ) -> None:
        """Show supported device types and platform information."""
        setup_logging("DEBUG" if verbose else "INFO")

        ctx = CommandContext()

        try:
            # Use the local implementation
            _show_supported_types_impl(ctx, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    # Register the list command group with the main app
    app.add_typer(list_app, name="list", rich_help_panel="Info & Configuration")
