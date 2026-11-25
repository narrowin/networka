# SPDX-License-Identifier: MIT
"""`nw info` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.api.info import InfoOptions, get_info
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.credentials import (
    InteractiveCredentials,
    prompt_for_credentials,
)
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputManager,
    OutputMode,
    get_output_mode_from_config,
)
from network_toolkit.common.table_providers import (
    DeviceInfoTableProvider,
    DeviceTypesInfoTableProvider,
    GroupInfoTableProvider,
    SequenceInfoTableProvider,
    TransportTypesTableProvider,
)
from network_toolkit.config import NetworkConfig, load_inspection_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Info & Configuration",
    )
    def info(
        targets: Annotated[
            str,
            typer.Argument(
                help="Comma-separated device/group/sequence names from configuration"
            ),
        ],
        config_file: Annotated[
            Path | None,
            typer.Option("--config", "-c", help="Configuration directory or file path"),
        ] = None,
        vendor: Annotated[
            str | None,
            typer.Option(
                "--vendor",
                help="Show the sequence selected for a platform (e.g., cisco_iosxe, mikrotik_routeros)",
            ),
        ] = None,
        device: Annotated[
            str | None,
            typer.Option(
                "--device", help="Show the sequence selected for this configured device"
            ),
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
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
        trace: Annotated[
            bool,
            typer.Option(
                "--trace",
                "-t",
                help="Show verbose provenance with full file paths and line numbers",
            ),
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
        Show comprehensive information for devices, groups, or sequences.

        Supports comma-separated device names, group names, and sequence names.

        Examples:
        - nw info sw-acc1                    # Show device info
        - nw info sw-acc1 --trace            # Show device info with source provenance
        - nw info sw-acc1,sw-acc2           # Show multiple devices
        - nw info access_switches           # Show group info
        - nw info system_info               # Show sequence definitions by source
        - nw info system_info --vendor cisco_iosxe  # Show vendor-specific commands
        - nw info system_info --device sw-acc1  # Show the device's effective sequence
        - nw info sw-acc1,access_switches,health_check  # Mixed types
        """
        ctx = None
        try:
            if verbose and output_mode != OutputMode.RAW:
                setup_logging("DEBUG")
            config = load_inspection_config(config_file)
            ctx = CommandContext(
                config=config,
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
                ctx.print_info(f"Will use username: {interactive_creds.username}")

            options = InfoOptions(
                targets=targets,
                config=config,
                vendor=vendor,
                verbose=verbose,
                device=device,
            )

            result = get_info(options)

            # Show header for device information if we have devices
            if result.device_count > 0:
                ctx.print_info(
                    f"Device Information ({result.device_count} device{'s' if result.device_count != 1 else ''})"
                )

            unavailable = False
            for i, target in enumerate(result.targets):
                if i > 0:
                    ctx.print_blank_line()

                if target.type == "device":
                    _show_device_info(
                        target.name, config, ctx, interactive_creds, verbose, trace
                    )
                elif target.type == "group":
                    _show_group_info(target.name, config, ctx)
                elif target.type == "sequence":
                    if not target.sequence_records:
                        scope = f" for {device or vendor}" if device or vendor else ""
                        ctx.print_error(
                            f"Sequence '{target.name}' is not available{scope}."
                        )
                        unavailable = True
                    for record in target.sequence_records:
                        provider = SequenceInfoTableProvider(
                            record=record,
                            device=device,
                            vendor=vendor,
                        )
                        ctx.render_table(provider, verbose)

            for unknown in result.unknown_targets:
                ctx.print_warning(f"Unknown target: {unknown}")

            if unavailable or (not result.targets and result.unknown_targets):
                raise typer.Exit(1)

        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            output = (
                ctx.output_manager
                if ctx is not None
                else OutputManager(output_mode or get_output_mode_from_config())
            )
            if isinstance(e, NetworkToolkitError):
                output.print_error(f"Error: {e.message}")
                if verbose and e.details:
                    output.print_error(f"Details: {e.details}")
            else:
                output.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None


def _show_supported_types_impl(ctx: CommandContext, verbose: bool) -> None:
    """Implementation logic for showing supported device types."""
    # Show transport types first
    transport_provider = TransportTypesTableProvider()
    ctx.render_table(transport_provider, False)

    ctx.print_blank_line()

    # Show supported device types
    device_types_provider = DeviceTypesInfoTableProvider()
    ctx.render_table(device_types_provider, verbose)

    if verbose:
        # Show usage examples
        ctx.print_usage_examples_header()
        examples_text = """  # Use in device configuration:
  devices:
    my_device:
      host: 192.168.1.1
      device_type: mikrotik_routeros
      transport_type: scrapli  # Optional, defaults to scrapli

  # Use with IP addresses:
  nw run 192.168.1.1 "/system/identity/print" --platform mikrotik_routeros

  # Transport selection via config:
  general:
    default_transport_type: scrapli"""
        ctx.print_code_block(examples_text)


def _show_device_info(
    device: str,
    config: NetworkConfig,
    ctx: CommandContext,
    interactive_creds: InteractiveCredentials | None,
    verbose: bool,
    trace: bool = False,
) -> None:
    """Show detailed information for a device."""
    if not config.devices or device not in config.devices:
        ctx.print_error(f"Error: Device '{device}' not found in configuration")
        return

    provider = DeviceInfoTableProvider(
        config=config,
        device_name=device,
        interactive_creds=interactive_creds,
        config_path=ctx.config_file,
        show_provenance=True,
        verbose_provenance=trace,
    )
    ctx.render_table(provider, verbose)


def _show_group_info(target: str, config: NetworkConfig, ctx: CommandContext) -> None:
    """Show detailed information for a group."""
    if not config.device_groups or target not in config.device_groups:
        ctx.print_error(f"Error: Group '{target}' not found in configuration")
        return

    provider = GroupInfoTableProvider(
        config=config, group_name=target, config_path=ctx.config_file
    )
    ctx.render_table(provider, False)
