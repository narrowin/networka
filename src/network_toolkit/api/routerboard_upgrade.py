"""Programmatic API for RouterBOARD upgrade operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import UnsupportedOperationError, get_platform_operations

logger = logging.getLogger(__name__)


@dataclass
class RouterboardUpgradeOptions:
    """Options for RouterBOARD upgrade operation."""

    target: str
    config: NetworkConfig
    precheck_sequence: str = "pre_maintenance"
    skip_precheck: bool = False
    verbose: bool = False


@dataclass
class DeviceRouterboardUpgradeResult:
    """Result of RouterBOARD upgrade for a single device."""

    device_name: str
    success: bool
    message: str
    platform: str = "unknown"
    error_details: str | None = None


@dataclass
class RouterboardUpgradeResult:
    """Result of RouterBOARD upgrade operation."""

    results: list[DeviceRouterboardUpgradeResult] = field(default_factory=list)
    failed_count: int = 0
    success_count: int = 0


def upgrade_routerboard(
    options: RouterboardUpgradeOptions,
) -> RouterboardUpgradeResult:
    """Upgrade RouterBOARD firmware on network devices."""
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

    result = RouterboardUpgradeResult()

    for dev in target_devices:
        dev_result = _process_device_upgrade(dev, options)
        result.results.append(dev_result)
        if dev_result.success:
            result.success_count += 1
        else:
            result.failed_count += 1

    return result


def _process_device_upgrade(
    dev: str, options: RouterboardUpgradeOptions
) -> DeviceRouterboardUpgradeResult:
    """Process RouterBOARD upgrade for a single device."""
    try:
        with DeviceSession(dev, options.config) as session:
            # Get platform-specific operations
            try:
                platform_ops = get_platform_operations(session)
            except UnsupportedOperationError as e:
                return DeviceRouterboardUpgradeResult(
                    device_name=dev,
                    success=False,
                    message=str(e),
                )

            if options.precheck_sequence and not options.skip_precheck:
                logger.info(
                    "Running precheck sequence '%s' on %s",
                    options.precheck_sequence,
                    dev,
                )
                seq_cmds: list[str] = []
                dcfg = (options.config.devices or {}).get(dev)
                if (
                    dcfg
                    and dcfg.command_sequences
                    and options.precheck_sequence in dcfg.command_sequences
                ):
                    seq_cmds = dcfg.command_sequences[options.precheck_sequence]

                for cmd in seq_cmds:
                    session.execute_command(cmd)

            logger.warning("Upgrading BIOS/RouterBOOT on %s and rebooting...", dev)
            try:
                platform_name_obj = platform_ops.get_platform_name()
                platform_name = str(platform_name_obj)
            except Exception:
                platform_name = "unknown"

            # Use platform-specific BIOS upgrade
            ok = platform_ops.bios_upgrade()
            if ok:
                return DeviceRouterboardUpgradeResult(
                    device_name=dev,
                    success=True,
                    message="OK BIOS upgrade scheduled; device rebooting",
                    platform=platform_name,
                )
            return DeviceRouterboardUpgradeResult(
                device_name=dev,
                success=False,
                message="FAIL BIOS upgrade failed to start",
                platform=platform_name,
            )
    except NetworkToolkitError as e:
        return DeviceRouterboardUpgradeResult(
            device_name=dev,
            success=False,
            message=e.message,
            error_details=e.details,
        )
    except Exception as e:
        return DeviceRouterboardUpgradeResult(
            device_name=dev,
            success=False,
            message=f"Unexpected error: {e}",
        )
