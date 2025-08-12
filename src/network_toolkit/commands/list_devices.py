# SPDX-License-Identifier: MIT
"""`nw list-devices` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command("list-devices", rich_help_panel="Info & Configuration")
    def list_devices(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = Path("devices.yml"),
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
    ) -> None:
        """List all configured network devices."""
        setup_logging("DEBUG" if verbose else "INFO")
        try:
            config = load_config(config_file)

            console.print("[bold blue]Configured Devices[/bold blue]")
            console.print()

            if not config.devices:
                console.print("[yellow]No devices configured[/yellow]")
                return

            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Host", style="white")
            table.add_column("Type", style="yellow")
            table.add_column("Description", style="white")
            table.add_column("Tags", style="green")

            for name, device_config in config.devices.items():
                table.add_row(
                    name,
                    device_config.host,
                    device_config.device_type,
                    device_config.description or "N/A",
                    ", ".join(device_config.tags) if device_config.tags else "None",
                )

            console.print(table)
            console.print(f"\n[bold]Total devices: {len(config.devices)}[/bold]")

        except NetworkToolkitError as e:
            console.print(f"[red]Error: {e.message}[/red]")
            if verbose and e.details:
                console.print(f"[red]Details: {e.details}[/red]")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(1) from None
