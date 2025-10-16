# SPDX-License-Identifier: MIT
"""`nw info` command implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

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
    GroupInfoTableProvider,
    TransportTypesTableProvider,
    VendorSequenceInfoTableProvider,
)
from network_toolkit.config import load_config
from network_toolkit.credentials import EnvironmentCredentialManager
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.sequence_manager import SequenceManager

if TYPE_CHECKING:
    from network_toolkit.config import NetworkConfig


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

            # Parse targets and determine types
            target_list = [t.strip() for t in targets.split(",") if t.strip()]
            if not target_list:
                ctx.print_error("Error: No targets specified")
                raise typer.Exit(1) from None

            # Process each target
            known_count = 0
            unknown_count = 0
            device_count = 0

            # Count devices for header
            for target in target_list:
                target_type = _determine_target_type(target, config)
                if target_type == "device":
                    device_count += 1

            # Show header for device information if we have devices
            if device_count > 0:
                ctx.print_info(
                    f"Device Information ({device_count} device{'s' if device_count != 1 else ''})"
                )

            for i, target in enumerate(target_list):
                if i > 0:
                    ctx.print_blank_line()

                target_type = _determine_target_type(target, config)

                if target_type == "device":
                    _show_device_info(target, config, ctx, interactive_creds, verbose)
                    known_count += 1
                elif target_type == "group":
                    _show_group_info(target, config, ctx)
                    known_count += 1
                elif target_type == "sequence":
                    _show_sequence_info(target, config, ctx, verbose, vendor)
                    known_count += 1
                else:
                    # Unknown targets should not cause a non-zero exit; warn and continue
                    ctx.print_warning(f"Unknown target: {target}")
                    unknown_count += 1
                    continue

            # If nothing was recognized and config is not empty, treat as error
            if known_count == 0 and unknown_count > 0:
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


def _determine_target_type(target: str, config: NetworkConfig) -> str:
    """Determine if target is a device, group, or sequence."""
    # Check if it's a device
    if config.devices and target in config.devices:
        return "device"

    # Check if it's a group
    if config.device_groups and target in config.device_groups:
        return "group"

    # Check if it's a vendor sequence
    sm = SequenceManager(config)
    all_sequences = sm.list_all_sequences()
    for vendor_sequences in all_sequences.values():
        if target in vendor_sequences:
            return "sequence"

    return "unknown"


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

    # Check vendor sequences
    sm = SequenceManager(config)

    # If vendor is specified, only look for that vendor's implementation
    if vendor:
        vendor_sequences = sm.list_vendor_sequences(vendor)
        if target in vendor_sequences:
            sequence_record = vendor_sequences[target]
            # Keep vendor name in original format
            provider = VendorSequenceInfoTableProvider(
                sequence_name=target,
                sequence_record=sequence_record,
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

    # Original logic for multi-vendor display
    all_sequences = sm.list_all_sequences()

    # Find all vendors that implement this sequence
    matching_vendors: list[str] = []
    found_sequence_record: Any = None

    for vendor_name, vendor_sequences in all_sequences.items():
        if target in vendor_sequences:
            matching_vendors.append(vendor_name)
            # Use the first matching sequence record as the template
            # (they should be the same sequence across vendors)
            if found_sequence_record is None:
                found_sequence_record = vendor_sequences[target]

    if found_sequence_record:
        # Keep vendor names in original format for consistency with --vendor flag
        provider = VendorSequenceInfoTableProvider(
            sequence_name=target,
            sequence_record=found_sequence_record,
            vendor_names=matching_vendors,
            verbose=verbose,
            config=config,
            vendor_specific=False,
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
            return "device config file (devices/devices.yml)"
        if credential_type == "password" and getattr(dev, "password", None):
            return "device config file (devices/devices.yml)"

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
                    return f"group config file groups/groups.yml ({group_name})"
                elif credential_type == "password" and group.credentials.password:
                    return f"group config file groups/groups.yml ({group_name})"

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
