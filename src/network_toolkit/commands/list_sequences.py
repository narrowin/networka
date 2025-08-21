# SPDX-License-Identifier: MIT
"""`nw list-sequences` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import console, setup_logging
from network_toolkit.config import CommandSequence, load_config
from network_toolkit.sequence_manager import SequenceManager, SequenceRecord


def register(app: typer.Typer) -> None:
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
        verbose: Annotated[
            bool, typer.Option("--verbose", help="Show detailed information")
        ] = False,
    ) -> None:
        """List all available command sequences, optionally filtered by vendor or category."""
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            config = load_config(config_file)
            sm = SequenceManager(config)

            # Vendor sequences (built-in + repo + user + config)
            if vendor:
                vendor_seqs = sm.list_vendor_sequences(vendor)
                _show_vendor_sequences(vendor, vendor_seqs, category, verbose=verbose)
            else:
                all_vendor = sm.list_all_sequences()
                if all_vendor:
                    _show_all_vendor_sequences(all_vendor, category, verbose=verbose)
                else:
                    console.print(
                        "[yellow]No vendor-specific sequences found.[/yellow]"
                    )

            # Show global sequences if they exist
            if config.global_command_sequences:
                console.print("\n")
                _show_global_sequences(config.global_command_sequences, verbose=verbose)

        except Exception as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            raise typer.Exit(1) from e


def _show_vendor_sequences(
    vendor: str,
    sequences: dict[str, SequenceRecord],
    category_filter: str | None,
    *,
    verbose: bool,
) -> None:
    """Show sequences for a specific vendor."""
    console.print(f"[bold blue]Command Sequences for {vendor.title()}[/bold blue]")

    if not sequences:
        console.print("[yellow]No sequences found for this vendor.[/yellow]")
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
        console.print(
            f"[yellow]No sequences found for category '{category_filter}'.[/yellow]"
        )
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Sequence Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Commands", style="dim")

    if verbose:
        table.add_column("Timeout", style="blue")
        table.add_column("Device Types", style="red")

    preview_limit = 3
    for name, seq in filtered_sequences.items():
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

    console.print(table)


def _show_all_vendor_sequences(
    sequences: dict[str, dict[str, SequenceRecord]],
    category_filter: str | None,
    *,
    verbose: bool,
) -> None:
    """Show sequences for all vendors."""
    console.print("[bold blue]Command Sequences by Vendor[/bold blue]")

    for vendor, vendor_sequences in sequences.items():
        console.print(f"\n[bold cyan]{vendor.replace('_', ' ').title()}[/bold cyan]")

        # Filter by category if specified
        filtered_sequences = vendor_sequences
        if category_filter:
            filtered_sequences = {
                name: seq
                for name, seq in vendor_sequences.items()
                if hasattr(seq, "category") and seq.category == category_filter
            }

        if not filtered_sequences:
            console.print(f"  [dim]No sequences for category '{category_filter}'[/dim]")
            continue

        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Category", style="yellow")

        if verbose:
            table.add_column("Commands", style="dim")

        for name, seq in filtered_sequences.items():
            row = [
                name,
                seq.description or "No description",
                seq.category or "general",
            ]

            if verbose:
                commands_str = str(len(seq.commands)) + " commands"
                row.append(commands_str)

            table.add_row(*row)

        console.print(table)


def _show_global_sequences(
    sequences: dict[str, CommandSequence], *, verbose: bool
) -> None:
    """Show global sequences."""
    console.print("[bold blue]Global Command Sequences[/bold blue]")

    # Filter by category if specified (global sequences don't have categories currently)
    filtered_sequences = sequences

    if not filtered_sequences:
        console.print("[yellow]No global sequences found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Sequence Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Commands", style="dim")

    if verbose:
        table.add_column("Tags", style="yellow")

    preview_limit = 3
    for name, seq in filtered_sequences.items():
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

    console.print(table)
