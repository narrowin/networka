# SPDX-License-Identifier: MIT
"""Platform factory for creating platform-specific operation handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from network_toolkit.platforms.base import PlatformOperations, UnsupportedOperationError

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
        # List supported platforms for error message
        supported_platforms = [
            "mikrotik_routeros",
            "cisco_ios",
            "cisco_iosxe",
        ]

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
    return {
        "mikrotik_routeros": "MikroTik RouterOS",
        "cisco_ios": "Cisco IOS",
        "cisco_iosxe": "Cisco IOS-XE",
    }


def is_platform_supported(device_type: str) -> bool:
    """Check if a device type/platform is supported.

    Parameters
    ----------
    device_type : str
        Device type to check

    Returns
    -------
    bool
        True if platform is supported
    """
    return device_type in get_supported_platforms()


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
    if not is_platform_supported(device_type):
        platforms = get_supported_platforms()
        supported_list = ", ".join(platforms.keys())
        return (
            False,
            f"Platform '{device_type}' is not supported. Supported platforms: {supported_list}",
        )

    # Get platform name for error messages
    platform_name = get_supported_platforms()[device_type]

    # For our current implementation, Cisco platforms don't support firmware operations
    if device_type in ["cisco_ios", "cisco_iosxe"] and operation_name in [
        "firmware_upgrade",
        "firmware_downgrade",
        "bios_upgrade",
        "create_backup",
    ]:
        return (
            False,
            f"Operation '{operation_name}' is not supported on platform '{platform_name}'",
        )

    # MikroTik RouterOS supports all operations
    if device_type == "mikrotik_routeros":
        return True, ""

    # Default case for unknown operations
    return (
        False,
        f"Operation '{operation_name}' is not supported on platform '{platform_name}'",
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
    if device_type == "mikrotik_routeros":
        from network_toolkit.platforms.mikrotik_routeros.constants import (
            SUPPORTED_FIRMWARE_EXTENSIONS,
        )

        return SUPPORTED_FIRMWARE_EXTENSIONS
    elif device_type == "cisco_ios":
        from network_toolkit.platforms.cisco_ios.constants import (
            SUPPORTED_FIRMWARE_EXTENSIONS,
        )

        return SUPPORTED_FIRMWARE_EXTENSIONS
    elif device_type == "cisco_iosxe":
        from network_toolkit.platforms.cisco_iosxe.constants import (
            SUPPORTED_FIRMWARE_EXTENSIONS,
        )

        return SUPPORTED_FIRMWARE_EXTENSIONS
    else:
        return []
