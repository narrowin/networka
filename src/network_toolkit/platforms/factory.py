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
