# SPDX-License-Identifier: MIT
"""`nw info` command implementation - Refactored with unified command base."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.command import CommandContext, handle_toolkit_errors
from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.output import OutputMode
from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from network_toolkit.config import NetworkConfig


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Info & Configuration")
    @handle_toolkit_errors
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
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
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
        # Create unified command context
        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        # Handle interactive authentication if requested
        interactive_creds = None
        if interactive_auth:
            ctx.print_warning("Interactive authentication mode enabled")
            interactive_creds = prompt_for_credentials(
                "Enter username for devices",
                "Enter password for devices",
                "admin",  # Default username suggestion
            )
            ctx.print_success(f"Will use username: {interactive_creds.username}")

        # Resolve targets to device names
        resolver = DeviceResolver(ctx.config)
        devices, unknowns = resolver.resolve_targets(targets)

        if unknowns:
            ctx.output.print_unknown_warning(unknowns)

        if not devices:
            ctx.output.print_error("No valid devices found in targets")
            raise typer.Exit(1) from None

        ctx.output.print_info(f"Device Information ({len(devices)} devices)")

        # Show info for each resolved device
        for i, device in enumerate(devices):
            if i > 0:
                ctx.output.print_blank_line()  # Blank line between devices

            if not ctx.config.devices or device not in ctx.config.devices:
                ctx.output.print_error(f"Device '{device}' not found in configuration")
                continue

            device_config = ctx.config.devices[device]

            # Create device info table
            table = ctx.output.create_table(
                title=f"Device: {device}",
                show_header=False,
                box=None,
            )

            # Basic device information
            table.add_row("Host", str(device_config.host))
            table.add_row("Type", device_config.device_type)

            if device_config.description:
                table.add_row("Description", device_config.description)

            if device_config.tags:
                table.add_row("Tags", ", ".join(device_config.tags))

            if device_config.platform:
                table.add_row("Platform", device_config.platform)

            if device_config.model:
                table.add_row("Model", device_config.model)

            # Transport information
            transport_type = getattr(device_config, "transport_type", "scrapli")
            table.add_row("Transport", transport_type)

            # Connection test
            try:
                from network_toolkit.cli import DeviceSession

                # Get credential overrides if in interactive mode
                username_override = (
                    interactive_creds.username if interactive_creds else None
                )
                password_override = (
                    interactive_creds.password if interactive_creds else None
                )

                with DeviceSession(
                    device, ctx.config, username_override, password_override
                ) as session:
                    identity_result = session.execute_command("/system/identity/print")
                    table.add_row("Status", "Connected OK")
                    if identity_result:
                        lines = identity_result.strip().split("\n")
                        if lines:
                            identity = lines[0].strip()
                            table.add_row("Identity", identity)

            except NetworkToolkitError as e:
                table.add_row("Status", "Failed")
                table.add_row("Error", e.message)
                if ctx.verbose and e.details:
                    table.add_row("Details", str(e.details))
            except Exception as e:
                table.add_row("Status", "Failed")
                table.add_row("Error", str(e))

            ctx.output.print_table(table)
