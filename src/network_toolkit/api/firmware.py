"""Programmatic API for firmware operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import (
    check_operation_support,
    get_platform_file_extensions,
    get_platform_operations,
)

logger = logging.getLogger(__name__)


@dataclass
class FirmwareUpgradeOptions:
    """Options for firmware upgrade operation."""

    target: str
    firmware_file: Path
    config: NetworkConfig
    precheck_sequence: str = "pre_maintenance"
    skip_precheck: bool = False
    verbose: bool = False


@dataclass
class DeviceUpgradeResult:
    """Result of firmware upgrade for a single device."""

    device_name: str
    success: bool
    message: str
    platform: str = "unknown"
    transport: str = "unknown"
    error_details: str | None = None


@dataclass
class FirmwareUpgradeResult:
    """Result of firmware upgrade operation."""

    results: list[DeviceUpgradeResult] = field(default_factory=list)
    failed_count: int = 0
    success_count: int = 0


def upgrade_firmware(options: FirmwareUpgradeOptions) -> FirmwareUpgradeResult:
    """Upgrade firmware on network devices."""
    if not options.firmware_file.exists() or not options.firmware_file.is_file():
        msg = f"Firmware file not found: {options.firmware_file}"
        raise NetworkToolkitError(msg)

    devices = options.config.devices or {}
    groups = options.config.device_groups or {}
    is_device = options.target in devices
    is_group = options.target in groups

    if not (is_device or is_group):
        msg = f"'{options.target}' not found as device or group in configuration"
        raise NetworkToolkitError(msg)

    target_devices: list[str] = []
    if is_device:
        target_devices = [options.target]
    else:
        try:
            target_devices = options.config.get_group_members(options.target)
        except Exception:
            grp = groups.get(options.target)
            if grp and getattr(grp, "members", None):
                target_devices = grp.members or []

    if not target_devices:
        msg = f"No devices found in group '{options.target}'"
        raise NetworkToolkitError(msg)

    result = FirmwareUpgradeResult()

    for dev in target_devices:
        dev_result = _process_device_upgrade(dev, options)
        result.results.append(dev_result)
        if dev_result.success:
            result.success_count += 1
        else:
            result.failed_count += 1

    return result


def _process_device_upgrade(
    dev: str, options: FirmwareUpgradeOptions
) -> DeviceUpgradeResult:
    """Process firmware upgrade for a single device."""
    try:
        devices = options.config.devices or {}
        if dev not in devices:
            return DeviceUpgradeResult(
                device_name=dev,
                success=False,
                message=f"Device '{dev}' not found in configuration",
            )

        device_config = devices[dev]
        device_type = device_config.device_type

        # Check if platform supports firmware upgrade BEFORE connecting
        is_supported, error_msg = check_operation_support(
            device_type, "firmware_upgrade"
        )
        if not is_supported:
            return DeviceUpgradeResult(
                device_name=dev,
                success=False,
                message=f"Operation not supported: {error_msg}",
            )

        # Check supported file extensions before connecting
        supported_exts = get_platform_file_extensions(device_type)
        if options.firmware_file.suffix.lower() not in supported_exts:
            ext_list = ", ".join(supported_exts)
            platform_name = {
                "mikrotik_routeros": "MikroTik RouterOS",
                "cisco_ios": "Cisco IOS",
                "cisco_iosxe": "Cisco IOS-XE",
            }.get(device_type, device_type)
            return DeviceUpgradeResult(
                device_name=dev,
                success=False,
                message=(
                    f"Invalid firmware file for {platform_name}. "
                    f"Expected {ext_list}, got {options.firmware_file.suffix}"
                ),
            )

        # Connect to device and proceed with operation
        with DeviceSession(dev, options.config) as session:
            platform_ops = get_platform_operations(session)

            if options.precheck_sequence and not options.skip_precheck:
                logger.info(
                    "Running precheck sequence '%s' on %s...",
                    options.precheck_sequence,
                    dev,
                )
                # Run sequence commands
                seq_cmds: list[str] = []
                dcfg = devices.get(dev)
                if (
                    dcfg
                    and dcfg.command_sequences
                    and options.precheck_sequence in dcfg.command_sequences
                ):
                    seq_cmds = dcfg.command_sequences[options.precheck_sequence]

                for cmd in seq_cmds:
                    session.execute_command(cmd)

            logger.warning("Uploading firmware to %s and rebooting...", dev)

            transport_type = options.config.get_transport_type(dev)
            try:
                platform_name_obj = platform_ops.get_platform_name()
                platform_name = str(platform_name_obj)
            except Exception:
                platform_name = "unknown"

            # Use platform-specific firmware upgrade
            ok = platform_ops.firmware_upgrade(
                local_firmware_path=options.firmware_file
            )
            if ok:
                return DeviceUpgradeResult(
                    device_name=dev,
                    success=True,
                    message="OK Firmware upload initiated; device rebooting",
                    platform=platform_name,
                    transport=transport_type,
                )

            return DeviceUpgradeResult(
                device_name=dev,
                success=False,
                message="FAIL Firmware upgrade failed to start",
                platform=platform_name,
                transport=transport_type,
            )

    except NetworkToolkitError as e:
        return DeviceUpgradeResult(
            device_name=dev,
            success=False,
            message=e.message,
            error_details=e.details,
        )
    except Exception as e:
        return DeviceUpgradeResult(
            device_name=dev,
            success=False,
            message=f"Unexpected error: {e}",
        )
