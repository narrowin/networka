# SPDX-License-Identifier: MIT
"""`nw list-sequences` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputManager,
    OutputMode,
    get_output_manager_with_config,
)
from network_toolkit.common.styles import StyleManager, StyleName
from network_toolkit.config import CommandSequence, load_config
from network_toolkit.sequence_manager import SequenceManager, SequenceRecord

if TYPE_CHECKING:
    from network_toolkit.common.command_helpers import CommandContext
    from network_toolkit.config import NetworkConfig


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
    """Register the list-sequences command with the Typer app."""

    @app.command("list-sequences", rich_help_panel="Info & Configuration")
    def list_sequences(
        *,
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

        output_manager = None
        try:
            config = load_config(config_file)

            # Get output manager to determine mode
            if output_mode is not None:
                from network_toolkit.common.output import set_output_mode

                set_output_mode(output_mode)

            output_manager = get_output_manager_with_config(
                config.general.output_mode if output_mode is None else output_mode
            )

            # Create style manager for consistent theming
            style_manager = StyleManager(output_manager.mode)

            sm = SequenceManager(config)

            # Vendor sequences (built-in + repo + user + config)
            if vendor:
                vendor_seqs = sm.list_vendor_sequences(vendor)
                _show_vendor_sequences(
                    vendor, vendor_seqs, category, style_manager, verbose=verbose
                )
            else:
                all_vendor = sm.list_all_sequences()
                if all_vendor:
                    _show_all_vendor_sequences(
                        all_vendor, category, style_manager, verbose=verbose
                    )
                else:
                    output_manager.print_text(
                        style_manager.format_message(
                            "No vendor-specific sequences found.", StyleName.WARNING
                        )
                    )

            # Show global sequences if they exist
            if config.global_command_sequences:
                output_manager.print_blank_line()
                _show_global_sequences(
                    config.global_command_sequences,
                    style_manager,
                    output_manager,
                    verbose=verbose,
                )

        except Exception as e:
            # Create default style manager for error output
            style_manager = StyleManager(OutputMode.DEFAULT)
            # Use a default OutputManager for error display
            from network_toolkit.common.output import get_output_manager

            get_output_manager().print_text(
                style_manager.format_message(
                    f"Error loading configuration: {e}", StyleName.ERROR
                )
            )
            raise typer.Exit(1) from e


def _show_vendor_sequences(
    vendor: str,
    sequences: dict[str, SequenceRecord],
    category_filter: str | None,
    style_manager: StyleManager,
    *,
    verbose: bool,
) -> None:
    """Show sequences for a specific vendor."""
    from network_toolkit.common.output import get_output_manager

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
    verbose: bool,
) -> None:
    """Show sequences for all vendors."""
    from network_toolkit.common.output import get_output_manager

    output_manager = get_output_manager()
    output_manager.print_text(
        style_manager.format_message("Command Sequences by Vendor", StyleName.BOLD)
    )

    for vendor, vendor_sequences in sorted(sequences.items()):
        vendor_title = vendor.replace("_", " ").title()
        output_manager.print_text(
            f"\n{style_manager.format_message(vendor_title, StyleName.DEVICE)}"
        )

        # Filter by category if specified
        filtered_sequences = vendor_sequences
        if category_filter:
            filtered_sequences = {
                name: seq
                for name, seq in vendor_sequences.items()
                if hasattr(seq, "category") and seq.category == category_filter
            }

        if not filtered_sequences:
            output_manager.print_text(
                style_manager.format_message(
                    f"  No sequences for category '{category_filter}'", StyleName.DIM
                )
            )
            continue

        table = style_manager.create_table()
        style_manager.add_column(table, "Name", StyleName.DEVICE)
        style_manager.add_column(table, "Description", StyleName.SUCCESS)
        style_manager.add_column(table, "Category", StyleName.WARNING)

        if verbose:
            style_manager.add_column(table, "Commands", StyleName.DIM)

        for name, seq in sorted(filtered_sequences.items()):
            row = [name, seq.description or "No description", seq.category or "general"]
            if verbose:
                commands_str = str(len(seq.commands)) + " commands"
                row.append(commands_str)
            table.add_row(*row)

        output_manager.print_table(table)


def _show_global_sequences(
    sequences: dict[str, CommandSequence],
    style_manager: StyleManager,
    output_manager: OutputManager,
    *,
    verbose: bool,
) -> None:
    """Show global sequences."""
    output_manager.print_text(
        style_manager.format_message("Global Command Sequences", StyleName.BOLD)
    )

    # Filter by category if specified (global sequences don't have categories currently)
    filtered_sequences = sequences

    if not filtered_sequences:
        output_manager.print_text(
            style_manager.format_message(
                "No global sequences found.", StyleName.WARNING
            )
        )
        return

    table = style_manager.create_table()
    style_manager.add_column(table, "Sequence Name", StyleName.DEVICE)
    style_manager.add_column(table, "Description", StyleName.SUCCESS)
    style_manager.add_column(table, "Commands", StyleName.OUTPUT)

    if verbose:
        style_manager.add_column(table, "Tags", StyleName.WARNING)

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
            commands_str,
        ]

        if verbose:
            tags = ", ".join(seq.tags) if seq.tags else "none"
            row.append(tags)

        table.add_row(*row)

    output_manager.print_table(table)
