# SPDX-License-Identifier: MIT
"""`nw info` command implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.common.styles import StyleName
from network_toolkit.config import load_config
from network_toolkit.credentials import EnvironmentCredentialManager
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

        # Resolve default config path: if user passed the literal default 'config'
        # and it doesn't exist, fall back to the OS default config dir.
        cfg_path = Path(config_file)
        if str(cfg_path) == "config" and not cfg_path.exists():
            from network_toolkit.common.paths import default_modular_config_dir

            cfg_path = default_modular_config_dir()

        # Use CommandContext for consistent output management
        ctx = CommandContext(
            config_file=cfg_path,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(cfg_path)

            resolver = DeviceResolver(config)

            # Handle interactive authentication if requested
            interactive_creds = None
            if interactive_auth:
                ctx.print_warning("Interactive authentication mode enabled")
                interactive_creds = prompt_for_credentials(
                    "Enter username for devices",
                    "Enter password for devices",
                    "admin",  # Default username suggestion
                )
                ctx.print_info(f"Will use username: {interactive_creds.username}")

            # Resolve targets to device names
            devices, unknowns = resolver.resolve_targets(targets)

            if unknowns:
                ctx.print_warning(f"Unknown targets ignored: {', '.join(unknowns)}")

            if not devices:
                ctx.print_error("Error: No valid devices found in targets")
                raise typer.Exit(1) from None

            ctx.print_info(f"Device Information ({len(devices)} devices)")

            # Helper function to check if environment variable is truthy
            def _env_truthy(var_name: str) -> bool:
                val = os.getenv(var_name, "")
                return val.strip().lower() in {"1", "true", "yes", "y", "on"}

            # Helper function to determine credential source with exact filenames
            def get_credential_source(device_name: str, credential_type: str) -> str:
                """Get the source of a credential with exact file paths."""
                # Check interactive override
                if interactive_auth and interactive_creds:
                    if credential_type == "username" and interactive_creds.username:
                        return "interactive input"
                    if credential_type == "password" and interactive_creds.password:
                        return "interactive input"

                # Check device config
                dev = config.devices.get(device_name) if config.devices else None
                if dev:
                    if credential_type == "username" and getattr(dev, "user", None):
                        return "device config file (config/devices/devices.yml)"
                    if credential_type == "password" and getattr(dev, "password", None):
                        return "device config file (config/devices/devices.yml)"

                # Check device-specific environment variables
                env_var_name = f"NW_{credential_type.upper()}_{device_name.upper().replace('-', '_')}"
                if os.getenv(env_var_name):
                    return f"environment ({env_var_name})"

                # Check group-level credentials
                group_user, group_password = config.get_group_credentials(device_name)
                target_credential = (
                    group_user if credential_type == "username" else group_password
                )

                if target_credential:
                    # Find which group provided the credential
                    device_groups = config.get_device_groups(device_name)
                    for group_name in device_groups:
                        group = (
                            config.device_groups.get(group_name)
                            if config.device_groups
                            else None
                        )
                        if group and group.credentials:
                            if credential_type == "username" and group.credentials.user:
                                return f"group config file config/groups/groups.yml ({group_name})"
                            elif (
                                credential_type == "password"
                                and group.credentials.password
                            ):
                                return f"group config file config/groups/groups.yml ({group_name})"

                        # Check group environment variable
                        if EnvironmentCredentialManager.get_group_specific(
                            group_name, credential_type
                        ):
                            grp_env = f"NW_{credential_type.upper()}_{group_name.upper().replace('-', '_')}"
                            return f"environment ({grp_env})"

                # Check default environment variables
                default_env_var = f"NW_{credential_type.upper()}_DEFAULT"
                if os.getenv(default_env_var):
                    return f"environment ({default_env_var})"

                # Fallback to general config
                return f"config (general.default_{credential_type})"

            # Check if user wants to show plaintext passwords
            show_passwords = _env_truthy("NW_SHOW_PLAINTEXT_PASSWORDS")

            # Show info for each resolved device
            for i, device in enumerate(devices):
                if i > 0:
                    ctx.output_manager.print_blank_line()  # Blank line between devices

                if not config.devices or device not in config.devices:
                    ctx.print_error(
                        f"Error: Device '{device}' not found in configuration"
                    )
                    continue

                device_config = config.devices[device]

                table = ctx.style_manager.create_table(title=f"Device: {device}")
                ctx.style_manager.add_column(table, "Property", StyleName.DEVICE)
                ctx.style_manager.add_column(table, "Value", StyleName.OUTPUT)

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

                # Show actual username value and its source
                table.add_row("Username", conn_params["auth_username"])
                table.add_row(
                    "Username Source", get_credential_source(device, "username")
                )

                # Show password based on environment variable setting
                if show_passwords:
                    password_value = conn_params["auth_password"] or ""
                    table.add_row(
                        "Password", password_value
                    )  # pragma: allowlist secret
                else:
                    table.add_row("Password", "[hidden]")
                table.add_row(
                    "Password Source", get_credential_source(device, "password")
                )

                table.add_row("Timeout", f"{conn_params['timeout_socket']}s")

                # Show transport type
                transport_type = config.get_transport_type(device)
                table.add_row(
                    "Transport Type", f"[transport]{transport_type}[/transport]"
                )

                # Show group memberships
                group_memberships = []
                if config.device_groups:
                    for group_name, _group_config in config.device_groups.items():
                        if device in config.get_group_members(group_name):
                            group_memberships.append(group_name)

                if group_memberships:
                    table.add_row("Groups", ", ".join(group_memberships))

                ctx.output_manager.console.print(table)

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @app.command("supported-types", rich_help_panel="Info & Configuration")
    def supported_types(
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Show detailed information")
        ] = False,
    ) -> None:
        """Show supported device types and platform information."""
        setup_logging("DEBUG" if verbose else "INFO")

        ctx = CommandContext()

        from rich.table import Table

        from network_toolkit.config import get_supported_device_types
        from network_toolkit.ip_device import (
            get_supported_device_types as get_device_descriptions,
        )
        from network_toolkit.platforms.factory import (
            get_supported_platforms as get_platform_ops,
        )

        # Display available transports first
        ctx.output_manager.print_text(
            "[bold blue]Network Toolkit - Transport Types[/bold blue]\n"
        )

        transport_table = Table(title="Available Transport Types")
        transport_table.add_column("Transport", style="cyan", no_wrap=True)
        transport_table.add_column("Description", style="white")
        transport_table.add_column("Device Type Mapping", style="yellow")

        # Add known transports
        transport_table.add_row(
            "scrapli",
            "Async SSH/Telnet library with device-specific drivers",
            "Direct (uses device_type as-is)",
        )
        transport_table.add_row(
            "nornir_netmiko",
            "Netmiko library via Nornir framework",
            "Mapped (device_type → netmiko platform)",
        )

        ctx.output_manager.console.print(transport_table)
        ctx.output_manager.print_blank_line()

        # Display device types
        ctx.output_manager.print_text("[bold blue]Supported Device Types[/bold blue]\n")

        # Get all supported device types
        device_types = get_supported_device_types()
        device_descriptions = get_device_descriptions()
        platform_ops = get_platform_ops()

        # Create table
        table = Table(title="Device Types")
        table.add_column("Device Type", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Platform Ops", style="green")
        table.add_column("Transport Support", style="magenta")

        for device_type in sorted(device_types):
            description = device_descriptions.get(device_type, "No description")
            has_platform_ops = "✓" if device_type in platform_ops else "✗"

            # Show specific supported transports
            transport_support = "scrapli, nornir_netmiko"

            table.add_row(device_type, description, has_platform_ops, transport_support)

        ctx.output_manager.console.print(table)

        if verbose:
            ctx.output_manager.print_text(
                f"\n[bold]Total device types:[/bold] {len(device_types)}"
            )
            ctx.output_manager.print_text(
                f"[bold]With platform operations:[/bold] {len(platform_ops)}"
            )
            ctx.output_manager.print_text(
                "[bold]Available transports:[/bold] scrapli (default), nornir_netmiko"
            )

            # Show usage examples
            ctx.output_manager.print_text(
                "\n[bold yellow]Usage Examples:[/bold yellow]"
            )
            ctx.output_manager.print_text("  # Use in device configuration:")
            ctx.output_manager.print_text("  devices:")
            ctx.output_manager.print_text("    my_device:")
            ctx.output_manager.print_text("      host: 192.168.1.1")
            ctx.output_manager.print_text("      device_type: mikrotik_routeros")
            ctx.output_manager.print_text(
                "      transport_type: scrapli  # Optional, defaults to scrapli"
            )
            ctx.output_manager.print_text("")
            ctx.output_manager.print_text("  # Use with IP addresses:")
            ctx.output_manager.print_text(
                '  nw run 192.168.1.1 "/system/identity/print" --platform mikrotik_routeros'
            )
            ctx.output_manager.print_text("")
            ctx.output_manager.print_text("  # Transport selection via config:")
            ctx.output_manager.print_text("  general:")
            ctx.output_manager.print_text("    default_transport_type: nornir_netmiko")
