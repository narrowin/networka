# SPDX-License-Identifier: MIT
"""`nw info` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputMode,
    get_output_manager,
    set_output_mode,
)
from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from network_toolkit.config import NetworkConfig


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Info & Configuration")
    def info(
        targets: Annotated[
            str,
            typer.Argument(help="Comma-separated device/group names from configuration"),
        ],
        config_file: Annotated[
            Path,
            typer.Option("--config", "-c", help="Configuration directory or file path"),
        ] = Path("config"),
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: normal, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose logging")] = False,
        interactive_auth: Annotated[
            bool,
            typer.Option(
                "--interactive-auth",
                "-i",
                help="Prompt for username and password interactively",
            ),
        ] = False,
    ) -> None:
        """
        Show comprehensive device information and connection status.

        Supports comma-separated device and group names.

        Examples:
        - nw info sw-acc1
        - nw info sw-acc1,sw-acc2
        - nw info access_switches
        - nw info sw-acc1,access_switches
        """
        setup_logging("DEBUG" if verbose else "INFO")

        # Handle output mode configuration
        if output_mode is None:
            output_mode = OutputMode.NORMAL
        set_output_mode(output_mode)

        # Get the output manager console
        console = get_output_manager().console

        try:
            config = load_config(config_file)
            resolver = DeviceResolver(config)

            # Handle interactive authentication if requested
            interactive_creds = None
            if interactive_auth:
                console.print("[yellow]Interactive authentication mode enabled[/yellow]")
                interactive_creds = prompt_for_credentials(
                    "Enter username for devices",
                    "Enter password for devices",
                    "admin",  # Default username suggestion
                )
                console.print(f"[green]Will use username: {interactive_creds.username}[/green]")

            # Resolve targets to device names
            devices, unknowns = resolver.resolve_targets(targets)

            if unknowns:
                console.print(f"[yellow]Warning: Unknown targets: {', '.join(unknowns)}[/yellow]")

            if not devices:
                console.print("[red]Error: No valid devices found in targets[/red]")
                raise typer.Exit(1) from None

            console.print(f"[bold blue]Device Information ({len(devices)} devices)[/bold blue]")

            # Show info for each resolved device
            for i, device in enumerate(devices):
                if i > 0:
                    console.print()  # Blank line between devices

                if not config.devices or device not in config.devices:
                    console.print(f"[red]Error: Device '{device}' not found in " "configuration[/red]")
                    continue

                device_config = config.devices[device]

                table = Table(title=f"Device: {device}")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")

                table.add_row("Host", device_config.host)
                table.add_row("Description", device_config.description or "N/A")
                table.add_row("Device Type", device_config.device_type)
                table.add_row("Model", device_config.model or "N/A")
                table.add_row("Platform", device_config.platform or "N/A")
                table.add_row("Location", device_config.location or "N/A")
                table.add_row(
                    "Tags",
                    ", ".join(device_config.tags) if device_config.tags else "None",
                )

                # Get connection params with optional credential overrides
                username_override = interactive_creds.username if interactive_creds else None
                password_override = interactive_creds.password if interactive_creds else None

                conn_params = config.get_device_connection_params(device, username_override, password_override)
                table.add_row("SSH Port", str(conn_params["port"]))
                table.add_row("Username", conn_params["auth_username"])
                table.add_row("Timeout", f"{conn_params['timeout_socket']}s")

                # Show transport type
                transport_type = config.get_transport_type(device)
                table.add_row("Transport Type", f"[yellow]{transport_type}[/yellow]")

                # Show credential source
                if interactive_auth:
                    table.add_row("Credentials", "[green]Interactive input[/green]")
                else:
                    table.add_row("Credentials", "[cyan]Environment/Config[/cyan]")

                # Show group memberships
                group_memberships = []
                if config.device_groups:
                    for group_name, _group_config in config.device_groups.items():
                        if device in config.get_group_members(group_name):
                            group_memberships.append(group_name)

                if group_memberships:
                    table.add_row("Groups", ", ".join(group_memberships))

                console.print(table)

        except NetworkToolkitError as e:
            console.print(f"[red]Error: {e.message}[/red]")
            if verbose and e.details:
                console.print(f"[red]Details: {e.details}[/red]")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(1) from None
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(1) from None
