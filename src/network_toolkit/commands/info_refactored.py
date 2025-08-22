# SPDX-License-Identifier: MIT
"""`nw info` command implementation - Refactored with unified command base."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from network_toolkit.common.command import CommandContext, handle_toolkit_errors
from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.output import OutputMode
from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.common.styles import StyleManager, StyleName
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

        # Create style manager for consistent theming
        style_manager = StyleManager(ctx.output_mode)

        def add_table_row(
            table: Table,
            label: str,
            value: str,
            label_style: StyleName = StyleName.COMMAND,
        ) -> None:
            """Helper to add consistently styled table rows."""
            table.add_row(style_manager.format_message(label, label_style), value)

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
            ctx.print_warning(f"Unknown targets: {', '.join(unknowns)}")

        if not devices:
            ctx.print_error("No valid devices found in targets")
            raise typer.Exit(1) from None

        ctx.console.print(
            style_manager.format_message(
                f"Device Information ({len(devices)} devices)", StyleName.INFO
            )
        )

        # Show info for each resolved device
        for i, device in enumerate(devices):
            if i > 0:
                ctx.console.print()  # Blank line between devices

            if not ctx.config.devices or device not in ctx.config.devices:
                ctx.print_error(f"Device '{device}' not found in configuration")
                continue

            device_config = ctx.config.devices[device]

            # Create device info table
            table = Table(
                title=f"Device: {device}",
                box=None,
                show_header=False,
                padding=(0, 1),
            )

            # Basic device information
            add_table_row(table, "Host", str(device_config.host))
            add_table_row(table, "Type", device_config.device_type)

            if device_config.description:
                add_table_row(table, "Description", device_config.description)

            if device_config.tags:
                add_table_row(table, "Tags", ", ".join(device_config.tags))

            if device_config.platform:
                add_table_row(table, "Platform", device_config.platform)

            if device_config.model:
                add_table_row(table, "Model", device_config.model)

            # Transport information
            transport_type = getattr(device_config, "transport_type", "scrapli")
            add_table_row(table, "Transport", transport_type)

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
                    add_table_row(
                        table,
                        "Status",
                        style_manager.format_message(
                            "Connected OK", StyleName.CONNECTED
                        ),
                        StyleName.SUCCESS,
                    )
                    if identity_result:
                        lines = identity_result.strip().split("\n")
                        if lines:
                            identity = lines[0].strip()
                            add_table_row(table, "Identity", identity)

            except NetworkToolkitError as e:
                add_table_row(
                    table,
                    "Status",
                    style_manager.format_message("Failed FAIL", StyleName.FAILED),
                    StyleName.ERROR,
                )
                add_table_row(
                    table,
                    "Error",
                    style_manager.format_message(e.message, StyleName.FAILED),
                    StyleName.ERROR,
                )
                if ctx.verbose and e.details:
                    add_table_row(
                        table,
                        "Details",
                        style_manager.format_message(str(e.details), StyleName.FAILED),
                        StyleName.ERROR,
                    )
            except Exception as e:
                add_table_row(
                    table,
                    "Status",
                    style_manager.format_message("Failed FAIL", StyleName.FAILED),
                    StyleName.ERROR,
                )
                add_table_row(
                    table,
                    "Error",
                    style_manager.format_message(str(e), StyleName.FAILED),
                    StyleName.ERROR,
                )

            ctx.console.print(table)
