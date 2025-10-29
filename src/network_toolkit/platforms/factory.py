# SPDX-License-Identifier: MIT
"""Platform factory for creating platform-specific operation handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from network_toolkit.platforms.base import PlatformOperations, UnsupportedOperationError
from network_toolkit.platforms.registry import (
    PLATFORM_REGISTRY,
    PlatformStatus,
    get_implemented_platforms,
)

if TYPE_CHECKING:
    from network_toolkit.device import DeviceSession


def get_platform_operations(session: DeviceSession) -> PlatformOperations:
    """Get platform-specific operations handler for a device session.

    Parameters
    ----------
    session : DeviceSession
        Device session containing device configuration

    Returns
    -------
    PlatformOperations
        Platform-specific operations handler

    Raises
    ------
    UnsupportedOperationError
        If the device platform is not supported
    """
    # Get device configuration to determine platform
    device_name = session.device_name
    config = session.config

    devices = config.devices or {}
    if device_name not in devices:
        msg = f"Device '{device_name}' not found in configuration"
        raise ValueError(msg)

    device_config = devices[device_name]
    device_type = device_config.device_type

    # Import platform-specific implementations
    if device_type == "mikrotik_routeros":
        from network_toolkit.platforms.mikrotik_routeros.operations import (
            MikroTikRouterOSOperations,
        )

        return MikroTikRouterOSOperations(session)

    elif device_type == "cisco_ios":
        from network_toolkit.platforms.cisco_ios.operations import CiscoIOSOperations

        return CiscoIOSOperations(session)

    elif device_type == "cisco_iosxe":
        from network_toolkit.platforms.cisco_iosxe.operations import (
            CiscoIOSXEOperations,
        )

        return CiscoIOSXEOperations(session)

    else:
        # List supported platforms for error message using registry
        implemented = get_implemented_platforms()
        supported_platforms = list(implemented.keys())

        msg = (
            f"Platform operations not implemented for device type '{device_type}'. "
            f"Supported platforms: {', '.join(supported_platforms)}"
        )
        raise UnsupportedOperationError(device_type, "platform_operations")


def get_supported_platforms() -> dict[str, str]:
    """Get mapping of supported platform device types to descriptions.

    Returns
    -------
    dict[str, str]
        Mapping of device_type to platform description
    """
    implemented = get_implemented_platforms()
    return {device_type: info.display_name for device_type, info in implemented.items()}


def is_platform_supported(device_type: str) -> bool:
    """Check if a device type/platform is supported.

    Parameters
    ----------
    device_type : str
        Device type to check

    Returns
    -------
    bool
        True if platform is supported and fully implemented
    """
    platform_info = PLATFORM_REGISTRY.get(device_type)
    return (
        platform_info is not None and platform_info.status == PlatformStatus.IMPLEMENTED
    )


def check_operation_support(device_type: str, operation_name: str) -> tuple[bool, str]:
    """Check if a specific operation is supported by a platform.

    Parameters
    ----------
    device_type : str
        Device type to check
    operation_name : str
        Name of the operation to check (e.g., 'firmware_upgrade')

    Returns
    -------
    tuple[bool, str]
        (is_supported, error_message_if_not_supported)
    """
    platform_info = PLATFORM_REGISTRY.get(device_type)

    if platform_info is None:
        implemented = get_implemented_platforms()
        supported_list = ", ".join(implemented.keys())
        return (
            False,
            f"Platform '{device_type}' is not supported. Supported platforms: {supported_list}",
        )

    if platform_info.status != PlatformStatus.IMPLEMENTED:
        return (
            False,
            f"Platform '{platform_info.display_name}' does not have full operations support yet (status: {platform_info.status.value})",
        )

    # Map operation names to capability fields
    capability_mapping = {
        "firmware_upgrade": "firmware_upgrade",
        "firmware_downgrade": "firmware_downgrade",
        "bios_upgrade": "bios_upgrade",
        "config_backup": "config_backup",
        "comprehensive_backup": "comprehensive_backup",
        "create_backup": "comprehensive_backup",  # Alias for comprehensive_backup
    }

    capability_field = capability_mapping.get(operation_name)
    if capability_field is None:
        return (
            False,
            f"Unknown operation '{operation_name}'",
        )

    is_supported = getattr(platform_info.capabilities, capability_field, False)
    if is_supported:
        return True, ""
    else:
        return (
            False,
            f"Operation '{operation_name}' is not supported on platform '{platform_info.display_name}'",
        )


def get_platform_file_extensions(device_type: str) -> list[str]:
    """Get supported file extensions for a platform without requiring a session.

    Parameters
    ----------
    device_type : str
        Device type to check

    Returns
    -------
    list[str]
        List of supported file extensions
    """
    platform_info = PLATFORM_REGISTRY.get(device_type)
    if platform_info is None:
        return []
    return platform_info.firmware_extensions
