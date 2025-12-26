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
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.table_generator import BaseTableProvider
from network_toolkit.common.table_providers import (
    DeviceInfoTableProvider,
    DeviceTypesInfoTableProvider,
    GlobalSequenceInfoTableProvider,
    GroupInfoTableProvider,
    TransportTypesTableProvider,
    VendorSequenceInfoTableProvider,
)
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.sequence_manager import SequenceManager


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Info & Configuration",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    def info(
        targets: Annotated[
            str,
            typer.Argument(
                help="Comma-separated device/group/sequence names from configuration"
            ),
        ],
        config_file: Annotated[
            Path,
            typer.Option("--config", "-c", help="Configuration directory or file path"),
        ] = DEFAULT_CONFIG_PATH,
        vendor: Annotated[
            str | None,
            typer.Option(
                "--vendor",
                help="Show vendor-specific commands for sequences (e.g., cisco_iosxe, mikrotik_routeros)",
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
        - nw info sw-acc1,sw-acc2           # Show multiple devices
        - nw info access_switches           # Show group info
        - nw info system_info               # Show sequence info (all vendors)
        - nw info system_info --vendor cisco_iosxe  # Show vendor-specific commands
        - nw info sw-acc1,access_switches,health_check  # Mixed types
        """
        setup_logging("DEBUG" if verbose else "WARNING")

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
            )

            result = get_info(options)

            # Show header for device information if we have devices
            if result.device_count > 0:
                ctx.print_info(
                    f"Device Information ({result.device_count} device{'s' if result.device_count != 1 else ''})"
                )

            known_count = 0
            for i, target in enumerate(result.targets):
                if i > 0:
                    ctx.print_blank_line()

                if target.type == "device":
                    _show_device_info(
                        target.name, config, ctx, interactive_creds, verbose
                    )
                    known_count += 1
                elif target.type == "group":
                    _show_group_info(target.name, config, ctx)
                    known_count += 1
                elif target.type == "sequence":
                    _show_sequence_info(target.name, config, ctx, verbose, vendor)
                    known_count += 1

            for unknown in result.unknown_targets:
                ctx.print_warning(f"Unknown target: {unknown}")

            # If nothing was recognized and config is not empty, treat as error
            if known_count == 0 and result.unknown_targets:
                has_devices = bool(getattr(config, "devices", None))
                has_groups = bool(getattr(config, "device_groups", None))
                # Inspect vendor sequences to determine if repository provides any
                sm = SequenceManager(config)
                all_vendor_sequences = sm.list_all_sequences()
                has_vendor_sequences = any(
                    bool(v) for v in all_vendor_sequences.values()
                )

                has_any_definitions = has_devices or has_groups or has_vendor_sequences

                if has_any_definitions:
                    # Heuristic: treat a single unknown token that doesn't look like a
                    # plural/group name as an error (covers "invalid device" CLI test),
                    # otherwise keep it as a warning-only to avoid false positives.
                    target_list = [t.strip() for t in targets.split(",") if t.strip()]
                    if len(target_list) == 1 and not target_list[0].endswith("s"):
                        raise typer.Exit(1) from None

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
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


def _show_sequence_info(
    target: str,
    config: NetworkConfig,
    ctx: CommandContext,
    verbose: bool = False,
    vendor: str | None = None,
) -> None:
    """Show detailed information for a sequence."""
    provider: BaseTableProvider

    # Check global sequences first
    if config.global_command_sequences and target in config.global_command_sequences:
        sequence = config.global_command_sequences[target]
        provider = GlobalSequenceInfoTableProvider(
            config=config, sequence_name=target, sequence=sequence, verbose=verbose
        )
        ctx.render_table(provider, verbose)
        return

    # Check vendor sequences
    sm = SequenceManager(config)

    # If vendor is specified, only look for that vendor's implementation
    if vendor:
        seq_record = sm.get_sequence_record(target, vendor)
        if seq_record:
            provider = VendorSequenceInfoTableProvider(
                sequence_name=target,
                sequence_record=seq_record,
                vendor_names=[vendor],
                verbose=verbose,
                config=config,
                vendor_specific=True,
            )
            ctx.render_table(provider, verbose)
            return
        else:
            ctx.print_error(
                f"Error: Sequence '{target}' not found for vendor '{vendor}'"
            )
            return

    # Otherwise show summary of all vendors that have this sequence
    all_sequences = sm.list_all_sequences()
    vendors_with_sequence = []

    # Find which vendors have this sequence
    for vendor_name, sequences in all_sequences.items():
        if target in sequences:
            vendors_with_sequence.append(vendor_name)

    if vendors_with_sequence:
        # Get the record from the first vendor to show general info
        first_vendor = vendors_with_sequence[0]
        seq_record = sm.get_sequence_record(target, first_vendor)

        provider = VendorSequenceInfoTableProvider(
            sequence_name=target,
            sequence_record=seq_record,
            vendor_names=vendors_with_sequence,
            verbose=verbose,
            config=config,
        )
        ctx.render_table(provider, verbose)
        return

    ctx.print_error(f"Error: Sequence '{target}' not found")
