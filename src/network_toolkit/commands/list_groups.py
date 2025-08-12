# SPDX-License-Identifier: MIT
"""`nw list-groups` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command("list-groups", rich_help_panel="Info & Configuration")
    def list_groups(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = Path("devices.yml"),
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Show detailed information")
        ] = False,
    ) -> None:
        """List all configured device groups and their members."""
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            config = load_config(config_file)

            console.print("[bold blue]Device Groups[/bold blue]")
            console.print()

            if not config.device_groups:
                console.print("[yellow]No device groups configured[/yellow]")
                return

            table = Table()
            table.add_column("Group Name", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Match Tags", style="yellow")
            table.add_column("Members", style="green")

            for name, group in config.device_groups.items():
                members: list[str] = []
                if group.members:
                    members = group.members
                elif group.match_tags and config.devices:
                    for device_name, device_config in config.devices.items():
                        if device_config.tags and any(
                            tag in device_config.tags for tag in group.match_tags
                        ):
                            members.append(device_name)

                table.add_row(
                    name,
                    group.description,
                    ", ".join(group.match_tags) if group.match_tags else "N/A",
                    ", ".join(members) if members else "None",
                )

            console.print(table)
            console.print(f"\n[bold]Total groups: {len(config.device_groups)}[/bold]")

            if verbose:
                console.print("\n[bold green]Usage Examples:[/bold green]")
                for group_name in config.device_groups.keys():
                    console.print(f"  nw group-run {group_name} health_check")

        except NetworkToolkitError as e:
            console.print(f"[red]Error: {e.message}[/red]")
            if verbose and e.details:
                console.print(f"[red]Details: {e.details}[/red]")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(1) from None
