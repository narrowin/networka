"""Unified firmware command module."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.styles import StyleName
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import (
    check_operation_support,
    get_platform_file_extensions,
    get_platform_operations,
)

MAX_LIST_PREVIEW = 10

# Create the firmware subapp
firmware_app = typer.Typer(
    name="firmware",
    help="Firmware management operations",
    no_args_is_help=True,
)


@firmware_app.command("upgrade")
def upgrade(
    target_name: Annotated[str, typer.Argument(help="Device or group name")],
    firmware_file: Annotated[Path, typer.Argument(help="Path to firmware file")],
    precheck_sequence: Annotated[
        str, typer.Option("--precheck-sequence", help="Pre-check sequence name")
    ] = "pre_maintenance",
    skip_precheck: Annotated[
        bool, typer.Option("--skip-precheck", help="Skip pre-check sequence")
    ] = False,
    config_file: Annotated[
        Path, typer.Option("--config", "-c", help="Configuration file path")
    ] = DEFAULT_CONFIG_PATH,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Upgrade firmware on network devices.

    Uploads and installs firmware upgrade on the specified device or group.
    """
    setup_logging("DEBUG" if verbose else "INFO")
    ctx = CommandContext(config_file=config_file, verbose=verbose, output_mode=None)
    style_manager = ctx.style_manager

    try:
        if not firmware_file.exists() or not firmware_file.is_file():
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: Firmware file not found: {firmware_file}",
                    StyleName.ERROR,
                )
            )
            raise typer.Exit(1)

        config = load_config(config_file)
        module = import_module("network_toolkit.cli")
        device_session = cast(Any, module).DeviceSession

        devices = config.devices or {}
        groups = config.device_groups or {}
        is_device = target_name in devices
        is_group = target_name in groups

        if not (is_device or is_group):
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: '{target_name}' not found as device or group in configuration",
                    StyleName.ERROR,
                )
            )
            if devices:
                dev_names = sorted(devices.keys())
                preview = ", ".join(dev_names[:MAX_LIST_PREVIEW])
                if len(dev_names) > MAX_LIST_PREVIEW:
                    preview += " ..."
                ctx.output_manager.print_text(
                    style_manager.format_message("Known devices:", StyleName.INFO)
                    + " "
                    + preview
                )
            if groups:
                grp_names = sorted(groups.keys())
                preview = ", ".join(grp_names[:MAX_LIST_PREVIEW])
                if len(grp_names) > MAX_LIST_PREVIEW:
                    preview += " ..."
                ctx.output_manager.print_text(
                    style_manager.format_message("Known groups:", StyleName.WARNING)
                    + " "
                    + preview
                )
            raise typer.Exit(1)

        def process_device(dev: str) -> bool:
            try:
                devices = config.devices or {}
                if dev not in devices:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error: Device '{dev}' not found in configuration",
                            StyleName.ERROR,
                        )
                    )
                    return False

                device_config = devices[dev]
                device_type = device_config.device_type

                # Check if platform supports firmware upgrade BEFORE connecting
                is_supported, error_msg = check_operation_support(
                    device_type, "firmware_upgrade"
                )
                if not is_supported:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error on {dev}: {error_msg}", StyleName.ERROR
                        )
                    )
                    return False

                # Check supported file extensions before connecting
                supported_exts = get_platform_file_extensions(device_type)
                if firmware_file.suffix.lower() not in supported_exts:
                    ext_list = ", ".join(supported_exts)
                    platform_name = {
                        "mikrotik_routeros": "MikroTik RouterOS",
                        "cisco_ios": "Cisco IOS",
                        "cisco_iosxe": "Cisco IOS-XE",
                    }.get(device_type, device_type)
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error: Invalid firmware file for {platform_name}. "
                            f"Expected {ext_list}, got {firmware_file.suffix}",
                            StyleName.ERROR,
                        )
                    )
                    return False

                # Connect to device and proceed with operation
                with device_session(dev, config) as session:
                    platform_ops = get_platform_operations(session)

                    if precheck_sequence and not skip_precheck:
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"Running precheck sequence '{precheck_sequence}' on {dev}...",
                                StyleName.INFO,
                            )
                        )
                        # Run sequence commands
                        seq_cmds: list[str] = []
                        dcfg = devices.get(dev)
                        if (
                            dcfg
                            and dcfg.command_sequences
                            and precheck_sequence in dcfg.command_sequences
                        ):
                            seq_cmds = dcfg.command_sequences[precheck_sequence]
                        elif (
                            config.global_command_sequences
                            and precheck_sequence in config.global_command_sequences
                        ):
                            seq_cmds = config.global_command_sequences[
                                precheck_sequence
                            ].commands

                        for cmd in seq_cmds:
                            session.execute_command(cmd)

                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Uploading firmware to {dev} and rebooting...",
                            StyleName.WARNING,
                        )
                    )

                    transport_type = config.get_transport_type(dev)
                    try:
                        platform_name_obj = platform_ops.get_platform_name()
                        platform_name = str(platform_name_obj)
                    except Exception:  # pragma: no cover
                        platform_name = "unknown"

                    ctx.output_manager.print_text(
                        style_manager.format_message("Platform:", StyleName.WARNING)
                        + f" {platform_name}"
                    )
                    ctx.output_manager.print_text(
                        style_manager.format_message("Transport:", StyleName.WARNING)
                        + f" {transport_type}"
                    )

                    # Use platform-specific firmware upgrade
                    ok = platform_ops.firmware_upgrade(
                        local_firmware_path=firmware_file
                    )
                    if ok:
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"OK Firmware upload initiated; device rebooting: {dev}",
                                StyleName.SUCCESS,
                            )
                        )
                        return True

                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"FAIL Firmware upgrade failed to start on {dev}",
                            StyleName.ERROR,
                        )
                    )
                    return False
            except NetworkToolkitError as e:
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Error on {dev}: {e.message}", StyleName.ERROR
                    )
                )
                if verbose and e.details:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Details: {e.details}", StyleName.ERROR
                        )
                    )
                return False
            except Exception as e:  # pragma: no cover
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Unexpected error on {dev}: {e}", StyleName.ERROR
                    )
                )
                return False

        if is_device:
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            return

        # Handle group
        members: list[str] = []
        try:
            members = config.get_group_members(target_name)
        except Exception:
            grp = groups.get(target_name)
            if grp and getattr(grp, "members", None):
                members = grp.members or []

        if not members:
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: No devices found in group '{target_name}'",
                    StyleName.ERROR,
                )
            )
            raise typer.Exit(1)

        ctx.output_manager.print_text(
            style_manager.format_message(
                f"Starting firmware upgrade for group '{target_name}' ({len(members)} devices)",
                StyleName.INFO,
            )
        )
        failures = 0
        for dev in members:
            ok = process_device(dev)
            failures += 0 if ok else 1

        total = len(members)
        ctx.output_manager.print_text(
            style_manager.format_message("Completed:", StyleName.BOLD)
            + f" {total - failures}/{total} initiated"
        )
        if failures:
            raise typer.Exit(1)

    except NetworkToolkitError as e:
        ctx.output_manager.print_text(
            style_manager.format_message(f"Error: {e.message}", StyleName.ERROR)
        )
        if verbose and e.details:
            ctx.output_manager.print_text(
                style_manager.format_message(f"Details: {e.details}", StyleName.ERROR)
            )
        raise typer.Exit(1) from None
    except Exception as e:  # pragma: no cover
        ctx.output_manager.print_text(
            style_manager.format_message(f"Unexpected error: {e}", StyleName.ERROR)
        )
        raise typer.Exit(1) from None


@firmware_app.command("downgrade")
def downgrade(
    target_name: Annotated[str, typer.Argument(help="Device or group name")],
    firmware_file: Annotated[Path, typer.Argument(help="Path to firmware file")],
    precheck_sequence: Annotated[
        str, typer.Option("--precheck-sequence", help="Pre-check sequence name")
    ] = "pre_maintenance",
    skip_precheck: Annotated[
        bool, typer.Option("--skip-precheck", help="Skip pre-check sequence")
    ] = False,
    config_file: Annotated[
        Path, typer.Option("--config", "-c", help="Configuration file path")
    ] = DEFAULT_CONFIG_PATH,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Downgrade firmware on network devices.

    Uploads and installs firmware downgrade on the specified device or group.
    """
    setup_logging("DEBUG" if verbose else "INFO")
    ctx = CommandContext(config_file=config_file, verbose=verbose, output_mode=None)
    style_manager = ctx.style_manager

    try:
        if not firmware_file.exists() or not firmware_file.is_file():
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: Firmware file not found: {firmware_file}",
                    StyleName.ERROR,
                )
            )
            raise typer.Exit(1)

        config = load_config(config_file)
        module = import_module("network_toolkit.cli")
        device_session = cast(Any, module).DeviceSession

        devices = config.devices or {}
        groups = config.device_groups or {}
        is_device = target_name in devices
        is_group = target_name in groups

        if not (is_device or is_group):
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: '{target_name}' not found as device or group in configuration",
                    StyleName.ERROR,
                )
            )
            raise typer.Exit(1)

        def process_device(dev: str) -> bool:
            try:
                devices = config.devices or {}
                if dev not in devices:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error: Device '{dev}' not found in configuration",
                            StyleName.ERROR,
                        )
                    )
                    return False

                device_config = devices[dev]
                device_type = device_config.device_type

                # Check if platform supports firmware downgrade
                is_supported, error_msg = check_operation_support(
                    device_type, "firmware_downgrade"
                )
                if not is_supported:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error on {dev}: {error_msg}", StyleName.ERROR
                        )
                    )
                    return False

                # Check supported file extensions
                supported_exts = get_platform_file_extensions(device_type)
                if firmware_file.suffix.lower() not in supported_exts:
                    ext_list = ", ".join(supported_exts)
                    platform_name = {
                        "mikrotik_routeros": "MikroTik RouterOS",
                        "cisco_ios": "Cisco IOS",
                        "cisco_iosxe": "Cisco IOS-XE",
                    }.get(device_type, device_type)
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error: Invalid firmware file for {platform_name}. "
                            f"Expected {ext_list}, got {firmware_file.suffix}",
                            StyleName.ERROR,
                        )
                    )
                    return False

                # Connect to device and perform downgrade
                with device_session(dev, config) as session:
                    platform_ops = get_platform_operations(session)

                    if precheck_sequence and not skip_precheck:
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"Running precheck sequence '{precheck_sequence}' on {dev}...",
                                StyleName.INFO,
                            )
                        )
                        # Run sequence commands
                        seq_cmds: list[str] = []
                        dcfg = devices.get(dev)
                        if (
                            dcfg
                            and dcfg.command_sequences
                            and precheck_sequence in dcfg.command_sequences
                        ):
                            seq_cmds = dcfg.command_sequences[precheck_sequence]
                        elif (
                            config.global_command_sequences
                            and precheck_sequence in config.global_command_sequences
                        ):
                            seq_cmds = config.global_command_sequences[
                                precheck_sequence
                            ].commands

                        for cmd in seq_cmds:
                            session.execute_command(cmd)

                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Downgrading firmware on {dev} and rebooting...",
                            StyleName.WARNING,
                        )
                    )

                    # Use platform-specific firmware downgrade
                    ok = platform_ops.firmware_downgrade(
                        local_firmware_path=firmware_file
                    )
                    if ok:
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"OK Firmware downgrade initiated; device rebooting: {dev}",
                                StyleName.SUCCESS,
                            )
                        )
                        return True

                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"FAIL Firmware downgrade failed to start on {dev}",
                            StyleName.ERROR,
                        )
                    )
                    return False
            except NetworkToolkitError as e:
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Error on {dev}: {e.message}", StyleName.ERROR
                    )
                )
                if verbose and e.details:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Details: {e.details}", StyleName.ERROR
                        )
                    )
                return False
            except Exception as e:  # pragma: no cover
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Unexpected error on {dev}: {e}", StyleName.ERROR
                    )
                )
                return False

        if is_device:
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            return

        # Handle group
        members: list[str] = []
        try:
            members = config.get_group_members(target_name)
        except Exception:
            grp = groups.get(target_name)
            if grp and getattr(grp, "members", None):
                members = grp.members or []

        if not members:
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: No devices found in group '{target_name}'",
                    StyleName.ERROR,
                )
            )
            raise typer.Exit(1)

        ctx.output_manager.print_text(
            style_manager.format_message(
                f"Starting firmware downgrade for group '{target_name}' ({len(members)} devices)",
                StyleName.INFO,
            )
        )
        failures = 0
        for dev in members:
            ok = process_device(dev)
            failures += 0 if ok else 1

        total = len(members)
        ctx.output_manager.print_text(
            style_manager.format_message("Completed:", StyleName.BOLD)
            + f" {total - failures}/{total} initiated"
        )
        if failures:
            raise typer.Exit(1)

    except NetworkToolkitError as e:
        ctx.output_manager.print_text(
            style_manager.format_message(f"Error: {e.message}", StyleName.ERROR)
        )
        if verbose and e.details:
            ctx.output_manager.print_text(
                style_manager.format_message(f"Details: {e.details}", StyleName.ERROR)
            )
        raise typer.Exit(1) from None
    except Exception as e:  # pragma: no cover
        ctx.output_manager.print_text(
            style_manager.format_message(f"Unexpected error: {e}", StyleName.ERROR)
        )
        raise typer.Exit(1) from None


@firmware_app.command("bios")
def bios(
    target_name: Annotated[str, typer.Argument(help="Device or group name")],
    precheck_sequence: Annotated[
        str, typer.Option("--precheck-sequence", help="Pre-check sequence name")
    ] = "pre_maintenance",
    skip_precheck: Annotated[
        bool, typer.Option("--skip-precheck", help="Skip pre-check sequence")
    ] = False,
    config_file: Annotated[
        Path, typer.Option("--config", "-c", help="Configuration file path")
    ] = DEFAULT_CONFIG_PATH,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Upgrade BIOS on network devices.

    Upgrades device BIOS/RouterBOOT using platform-specific implementations.
    """
    setup_logging("DEBUG" if verbose else "INFO")
    ctx = CommandContext(config_file=config_file, verbose=verbose, output_mode=None)
    style_manager = ctx.style_manager

    try:
        config = load_config(config_file)
        module = import_module("network_toolkit.cli")
        device_session = cast(Any, module).DeviceSession

        devices = config.devices or {}
        groups = config.device_groups or {}
        is_device = target_name in devices
        is_group = target_name in groups

        if not (is_device or is_group):
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: '{target_name}' not found as device or group in configuration",
                    StyleName.ERROR,
                )
            )
            raise typer.Exit(1)

        def process_device(dev: str) -> bool:
            try:
                devices = config.devices or {}
                if dev not in devices:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error: Device '{dev}' not found in configuration",
                            StyleName.ERROR,
                        )
                    )
                    return False

                device_config = devices[dev]
                device_type = device_config.device_type

                # Check if platform supports BIOS upgrade
                is_supported, error_msg = check_operation_support(
                    device_type, "bios_upgrade"
                )
                if not is_supported:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error on {dev}: {error_msg}", StyleName.ERROR
                        )
                    )
                    return False

                # Connect to device and perform BIOS upgrade
                with device_session(dev, config) as session:
                    platform_ops = get_platform_operations(session)

                    if precheck_sequence and not skip_precheck:
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"Running precheck sequence '{precheck_sequence}' on {dev}...",
                                StyleName.INFO,
                            )
                        )
                        # Run sequence commands
                        seq_cmds: list[str] = []
                        dcfg = devices.get(dev)
                        if (
                            dcfg
                            and dcfg.command_sequences
                            and precheck_sequence in dcfg.command_sequences
                        ):
                            seq_cmds = dcfg.command_sequences[precheck_sequence]
                        elif (
                            config.global_command_sequences
                            and precheck_sequence in config.global_command_sequences
                        ):
                            seq_cmds = config.global_command_sequences[
                                precheck_sequence
                            ].commands

                        for cmd in seq_cmds:
                            session.execute_command(cmd)

                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Upgrading BIOS on {dev} and rebooting...",
                            StyleName.WARNING,
                        )
                    )

                    # Use platform-specific BIOS upgrade
                    ok = platform_ops.bios_upgrade()
                    if ok:
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"OK BIOS upgrade initiated; device rebooting: {dev}",
                                StyleName.SUCCESS,
                            )
                        )
                        return True

                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"FAIL BIOS upgrade failed to start on {dev}",
                            StyleName.ERROR,
                        )
                    )
                    return False
            except NetworkToolkitError as e:
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Error on {dev}: {e.message}", StyleName.ERROR
                    )
                )
                if verbose and e.details:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Details: {e.details}", StyleName.ERROR
                        )
                    )
                return False
            except Exception as e:  # pragma: no cover
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Unexpected error on {dev}: {e}", StyleName.ERROR
                    )
                )
                return False

        if is_device:
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            return

        # Handle group
        members: list[str] = []
        try:
            members = config.get_group_members(target_name)
        except Exception:
            grp = groups.get(target_name)
            if grp and getattr(grp, "members", None):
                members = grp.members or []

        if not members:
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Error: No devices found in group '{target_name}'",
                    StyleName.ERROR,
                )
            )
            raise typer.Exit(1)

        ctx.output_manager.print_text(
            style_manager.format_message(
                f"Starting BIOS upgrade for group '{target_name}' ({len(members)} devices)",
                StyleName.INFO,
            )
        )
        failures = 0
        for dev in members:
            ok = process_device(dev)
            failures += 0 if ok else 1

        total = len(members)
        ctx.output_manager.print_text(
            style_manager.format_message("Completed:", StyleName.BOLD)
            + f" {total - failures}/{total} initiated"
        )
        if failures:
            raise typer.Exit(1)

    except NetworkToolkitError as e:
        ctx.output_manager.print_text(
            style_manager.format_message(f"Error: {e.message}", StyleName.ERROR)
        )
        if verbose and e.details:
            ctx.output_manager.print_text(
                style_manager.format_message(f"Details: {e.details}", StyleName.ERROR)
            )
        raise typer.Exit(1) from None
    except Exception as e:  # pragma: no cover
        ctx.output_manager.print_text(
            style_manager.format_message(f"Unexpected error: {e}", StyleName.ERROR)
        )
        raise typer.Exit(1) from None


@firmware_app.command("vendors")
def vendors() -> None:
    """Show which vendors support firmware operations.

    Lists all supported vendors and their firmware operation capabilities.
    """
    from network_toolkit.platforms.factory import (
        check_operation_support,
        get_supported_platforms,
    )

    platforms = get_supported_platforms()

    ctx = CommandContext()
    ctx.print_info("Vendor firmware operation support:")

    operations = [
        ("firmware_upgrade", "Firmware Upgrade"),
        ("firmware_downgrade", "Firmware Downgrade"),
        ("bios_upgrade", "BIOS Upgrade"),
    ]

    for device_type, vendor_name in platforms.items():
        ctx.print_info(f"\n{vendor_name} ({device_type}):")

        for op_name, op_display in operations:
            supported, _ = check_operation_support(device_type, op_name)
            status = "✓ Supported" if supported else "✗ Not supported"
            ctx.print_info(f"  {op_display}: {status}")


def register(app: typer.Typer) -> None:
    """Register the unified firmware command with the main CLI app."""
    app.add_typer(firmware_app, rich_help_panel="Vendor-Specific Remote Operations")
