# SPDX-License-Identifier: MIT
"""`nw info` command implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.credentials import InteractiveCredentials
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
from network_toolkit.credentials import EnvironmentCredentialManager
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.sequence_manager import SequenceManager

if TYPE_CHECKING:
    from network_toolkit.config import NetworkConfig


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Info & Configuration")
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
    ) -> None:
        """
        Show comprehensive information for devices, groups, or sequences.

        Supports comma-separated device names, group names, and sequence names.

        Examples:
        - nw info sw-acc1                    # Show device info
        - nw info sw-acc1,sw-acc2           # Show multiple devices
        - nw info access_switches           # Show group info
        - nw info system_info               # Show sequence info
        - nw info sw-acc1,access_switches,health_check  # Mixed types
        """
        # Create command context with automatic config loading
        ctx = CommandContext.from_standard_kwargs(
            config_file=config_file, verbose=verbose, output_mode=output_mode
        )

        try:
            config = ctx.config

            # Process targets (split comma-separated values)
            target_list = [t.strip() for t in targets.split(",") if t.strip()]

            for target_name in target_list:
                if target_name == "supported-types":
                    _show_supported_types_impl(ctx, verbose)
                else:
                    _handle_info_target(target_name, config, ctx, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            raise typer.Exit(1) from None


def _handle_info_target(
    target: str,
    config: NetworkConfig,
    ctx: CommandContext,
    verbose: bool,
) -> None:
    """Handle info for a single target (device, group, or sequence)."""
    # Check if it's a device
    if config.devices and target in config.devices:
        _show_device_info(target, config, ctx)
        return

    # Check if it's a group
    if config.device_groups and target in config.device_groups:
        _show_group_info(target, config, ctx)
        return

    # Check if it's a global sequence
    if config.global_command_sequences and target in config.global_command_sequences:
        _show_sequence_info(target, config, ctx, verbose)
        return

    # Check if it's a vendor sequence
    sequence_manager = SequenceManager(config)
    try:
        # Try all known vendor types to see if sequence exists
        vendors = ["mikrotik_routeros", "cisco_ios", "cisco_nxos"]  # Add more as needed
        for vendor in vendors:
            vendor_sequences = sequence_manager.list_vendor_sequences(vendor)
            if target in vendor_sequences:
                _show_sequence_info(target, config, ctx, verbose)
                return
    except Exception:
        pass  # If sequence manager fails, continue to show error

    # If not found anywhere, show error
    ctx.print_error(f"Target '{target}' not found in devices, groups, or sequences")
    raise typer.Exit(1)


def _show_device_info(device: str, config: NetworkConfig, ctx: CommandContext) -> None:
    """Show detailed information for a device."""
    if not config.devices or device not in config.devices:
        ctx.print_error(f"Device '{device}' not found in configuration")
        raise typer.Exit(1)

    provider = DeviceInfoTableProvider(config=config, device_name=device)
    ctx.render_table(provider, False)  # verbose not available in this context


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


def _determine_target_type(target: str, config: NetworkConfig) -> str:
    """Determine if target is a device, group, or sequence."""
    # Check if it's a device
    if config.devices and target in config.devices:
        return "device"

    # Check if it's a group
    if config.device_groups and target in config.device_groups:
        return "group"

    # Check if it's a global sequence
    if config.global_command_sequences and target in config.global_command_sequences:
        return "sequence"

    # Check if it's a vendor sequence
    sm = SequenceManager(config)
    all_sequences = sm.list_all_sequences()
    for vendor_sequences in all_sequences.values():
        if target in vendor_sequences:
            return "sequence"

    return "unknown"


def _show_group_info(target: str, config: NetworkConfig, ctx: CommandContext) -> None:
    """Show detailed information for a group."""
    if not config.device_groups or target not in config.device_groups:
        ctx.print_error(f"Error: Group '{target}' not found in configuration")
        return

    provider = GroupInfoTableProvider(config=config, group_name=target)
    ctx.render_table(provider, False)


def _show_sequence_info(
    target: str, config: NetworkConfig, ctx: CommandContext, verbose: bool = False
) -> None:
    """Show detailed information for a sequence."""
    provider: BaseTableProvider

    # Check global sequences first
    if config.global_command_sequences and target in config.global_command_sequences:
        sequence = config.global_command_sequences[target]
        provider = GlobalSequenceInfoTableProvider(
            sequence_name=target, sequence=sequence, verbose=verbose
        )
        ctx.render_table(provider, verbose)
        return

    # Check vendor sequences
    sm = SequenceManager(config)
    all_sequences = sm.list_all_sequences()

    # Find all vendors that implement this sequence
    matching_vendors: list[str] = []
    sequence_record = None

    for vendor, vendor_sequences in all_sequences.items():
        if target in vendor_sequences:
            matching_vendors.append(vendor)
            # Use the first matching sequence record as the template
            # (they should be the same sequence across vendors)
            if sequence_record is None:
                sequence_record = vendor_sequences[target]

    if sequence_record:
        # Format vendor names for display
        vendor_names = [vendor.replace("_", " ").title() for vendor in matching_vendors]

        provider = VendorSequenceInfoTableProvider(
            sequence_name=target,
            sequence_record=sequence_record,
            vendor_names=vendor_names,
            verbose=verbose,
        )
        ctx.render_table(provider, verbose)
        return

    ctx.print_error(f"Error: Sequence '{target}' not found in configuration")


def _env_truthy(var_name: str) -> bool:
    """Check if environment variable is truthy."""
    val = os.getenv(var_name, "")
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_credential_source(
    device_name: str,
    credential_type: str,
    config: NetworkConfig,
    interactive_auth: bool,
    interactive_creds: InteractiveCredentials | None,
) -> str:
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
    env_var_name = (
        f"NW_{credential_type.upper()}_{device_name.upper().replace('-', '_')}"
    )
    if os.getenv(env_var_name):
        return f"environment ({env_var_name})"

    # Check group-level credentials
    group_user, group_password = config.get_group_credentials(device_name)
    target_credential = group_user if credential_type == "username" else group_password

    if target_credential:
        # Find which group provided the credential
        device_groups = config.get_device_groups(device_name)
        for group_name in device_groups:
            group = (
                config.device_groups.get(group_name) if config.device_groups else None
            )
            if group and group.credentials:
                if credential_type == "username" and group.credentials.user:
                    return f"group config file config/groups/groups.yml ({group_name})"
                elif credential_type == "password" and group.credentials.password:
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
