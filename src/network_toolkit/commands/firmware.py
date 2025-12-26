"""Unified firmware command module."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.styles import StyleName
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import resolve_named_targets, select_named_target
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
    context_settings={"help_option_names": ["-h", "--help"]},
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
    setup_logging("DEBUG" if verbose else "WARNING")
    ctx = CommandContext(config_file=config_file, verbose=verbose, output_mode=None)
    style_manager = ctx.style_manager

    try:
        config = load_config(config_file)
        from network_toolkit.api.firmware import (
            FirmwareUpgradeOptions,
            upgrade_firmware,
        )

        options = FirmwareUpgradeOptions(
            target=target_name,
            firmware_file=firmware_file,
            config=config,
            precheck_sequence=precheck_sequence,
            skip_precheck=skip_precheck,
            verbose=verbose,
        )

        result = upgrade_firmware(options)

        # Render results
        is_group = result.success_count + result.failed_count > 1
        if is_group:
            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Starting firmware upgrade for group '{target_name}' ({len(result.results)} devices)",
                    StyleName.INFO,
                )
            )

        for dev_res in result.results:
            if dev_res.success:
                if dev_res.platform != "unknown":
                    ctx.output_manager.print_text(
                        style_manager.format_message("Platform:", StyleName.WARNING)
                        + f" {dev_res.platform}"
                    )
                if dev_res.transport != "unknown":
                    ctx.output_manager.print_text(
                        style_manager.format_message("Transport:", StyleName.WARNING)
                        + f" {dev_res.transport}"
                    )
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"OK {dev_res.message}: {dev_res.device_name}",
                        StyleName.SUCCESS,
                    )
                )
            elif "Firmware upgrade failed to start" in dev_res.message:
                if dev_res.platform != "unknown":
                    ctx.output_manager.print_text(
                        style_manager.format_message("Platform:", StyleName.WARNING)
                        + f" {dev_res.platform}"
                    )
                if dev_res.transport != "unknown":
                    ctx.output_manager.print_text(
                        style_manager.format_message("Transport:", StyleName.WARNING)
                        + f" {dev_res.transport}"
                    )
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"FAIL {dev_res.message} on {dev_res.device_name}",
                        StyleName.ERROR,
                    )
                )
            else:
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Error on {dev_res.device_name}: {dev_res.message}",
                        StyleName.ERROR,
                    )
                )
                if verbose and dev_res.error_details:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Details: {dev_res.error_details}", StyleName.ERROR
                        )
                    )

        if is_group:
            total = len(result.results)
            ctx.output_manager.print_text(
                style_manager.format_message("Completed:", StyleName.BOLD)
                + f" {result.success_count}/{total} initiated"
            )

        if result.failed_count > 0:
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
    setup_logging("DEBUG" if verbose else "WARNING")
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
        from network_toolkit.device import DeviceSession

        device_session = DeviceSession

        target_kind = select_named_target(config, target_name)
        if target_kind not in {"device", "group"}:
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

        if target_kind == "device":
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            return

        # Handle group
        members = resolve_named_targets(config, target_name).resolved_devices

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
    setup_logging("DEBUG" if verbose else "WARNING")
    ctx = CommandContext(config_file=config_file, verbose=verbose, output_mode=None)
    style_manager = ctx.style_manager

    try:
        config = load_config(config_file)
        from network_toolkit.device import DeviceSession

        device_session = DeviceSession

        target_kind = select_named_target(config, target_name)
        if target_kind not in {"device", "group"}:
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

        if target_kind == "device":
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            return

        # Handle group
        members = resolve_named_targets(config, target_name).resolved_devices

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
