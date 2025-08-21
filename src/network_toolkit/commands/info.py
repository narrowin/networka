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
    get_output_manager_with_config,
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
            typer.Argument(
                help="Comma-separated device/group names from configuration"
            ),
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
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
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
            output_mode = OutputMode.DEFAULT
        set_output_mode(output_mode)

        try:
            # Resolve default config path: if user passed the literal default 'config'
            # and it doesn't exist, fall back to the OS default config dir.
            cfg_path = Path(config_file)
            if str(cfg_path) == "config" and not cfg_path.exists():
                from network_toolkit.common.paths import default_modular_config_dir

                cfg_path = default_modular_config_dir()
            config = load_config(cfg_path)

            # Handle output mode configuration - check config first, then CLI override
            if output_mode is not None:
                # CLI parameter overrides everything
                set_output_mode(output_mode)
                output_manager = get_output_manager_with_config()
            else:
                # Use config-based output mode
                output_manager = get_output_manager_with_config(
                    config.general.output_mode
                )

            resolver = DeviceResolver(config)

            # Get themed console
            themed_console = output_manager.console

            # Handle interactive authentication if requested
            interactive_creds = None
            if interactive_auth:
                output_manager.print_warning("Interactive authentication mode enabled")
                interactive_creds = prompt_for_credentials(
                    "Enter username for devices",
                    "Enter password for devices",
                    "admin",  # Default username suggestion
                )
                output_manager.print_credential_info(
                    f"Will use username: {interactive_creds.username}"
                )

            # Resolve targets to device names
            devices, unknowns = resolver.resolve_targets(targets)

            if unknowns:
                output_manager.print_unknown_warning(unknowns)

            if not devices:
                output_manager.print_error("Error: No valid devices found in targets")
                raise typer.Exit(1) from None

            themed_console.print(
                f"[bold]Device Information ({len(devices)} devices)[/bold]"
            )

            # Show info for each resolved device
            for i, device in enumerate(devices):
                if i > 0:
                    themed_console.print()  # Blank line between devices

                if not config.devices or device not in config.devices:
                    output_manager.print_error(
                        f"Error: Device '{device}' not found in configuration"
                    )
                    continue

                device_config = config.devices[device]

                table = Table(title=f"Device: {device}")
                table.add_column("Property", style="device")
                table.add_column("Value", style="output")

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
                username_override = (
                    interactive_creds.username if interactive_creds else None
                )
                password_override = (
                    interactive_creds.password if interactive_creds else None
                )

                conn_params = config.get_device_connection_params(
                    device, username_override, password_override
                )
                table.add_row("SSH Port", str(conn_params["port"]))
                table.add_row("Username", conn_params["auth_username"])
                table.add_row("Timeout", f"{conn_params['timeout_socket']}s")

                # Show transport type
                transport_type = config.get_transport_type(device)
                table.add_row(
                    "Transport Type", f"[transport]{transport_type}[/transport]"
                )

                # Show credential source
                if interactive_auth:
                    table.add_row(
                        "Credentials", "[credential]Interactive input[/credential]"
                    )
                else:
                    table.add_row(
                        "Credentials", "[credential]Environment/Config[/credential]"
                    )

                # Show group memberships
                group_memberships = []
                if config.device_groups:
                    for group_name, _group_config in config.device_groups.items():
                        if device in config.get_group_members(group_name):
                            group_memberships.append(group_name)

                if group_memberships:
                    table.add_row("Groups", ", ".join(group_memberships))

                themed_console.print(table)

        except NetworkToolkitError as e:
            output_manager.print_error(f"Error: {e.message}")
            if verbose and e.details:
                output_manager.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            output_manager.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
