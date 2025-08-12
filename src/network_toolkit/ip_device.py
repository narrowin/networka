# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Support for creating device configurations from IP addresses."""

from __future__ import annotations

import ipaddress

from network_toolkit.config import DeviceConfig, NetworkConfig


def is_ip_address(target: str) -> bool:
    """
    Check if a string is a valid IP address.

    Parameters
    ----------
    target : str
        String to check

    Returns
    -------
    bool
        True if target is a valid IP address
    """
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False


def is_ip_list(target: str) -> bool:
    """
    Check if a string is a comma-separated list of IP addresses.

    Parameters
    ----------
    target : str
        String to check

    Returns
    -------
    bool
        True if all comma-separated parts are valid IP addresses
    """
    if "," not in target:
        return is_ip_address(target)

    parts = [part.strip() for part in target.split(",")]
    return all(is_ip_address(part) for part in parts if part)


def extract_ips_from_target(target: str) -> list[str]:
    """
    Extract IP addresses from a target string.

    Parameters
    ----------
    target : str
        Target string (single IP or comma-separated IPs)

    Returns
    -------
    list[str]
        List of IP addresses
    """
    if "," not in target:
        return [target.strip()]

    return [ip.strip() for ip in target.split(",") if ip.strip()]


def create_ip_device_config(
    ip: str,
    platform: str,
    device_type: str | None = None,
    port: int | None = None,
) -> DeviceConfig:
    """
    Create a DeviceConfig from an IP address and platform.

    Parameters
    ----------
    ip : str
        IP address of the device
    platform : str
        Scrapli platform identifier (e.g., 'mikrotik_routeros', 'cisco_iosxe')
    device_type : str | None
        Device type, defaults to platform if not provided
    port : int | None
        SSH port, defaults to 22 if not provided

    Returns
    -------
    DeviceConfig
        Device configuration for the IP
    """
    # Validate IP address
    try:
        ipaddress.ip_address(ip)
    except ValueError as e:
        msg = f"Invalid IP address '{ip}': {e}"
        raise ValueError(msg) from e

    # Use platform as device_type if not provided
    if device_type is None:
        device_type = platform

    # Default port to 22 if not provided
    if port is None:
        port = 22

    return DeviceConfig(
        host=ip,
        description=f"Dynamic device at {ip}",
        device_type=device_type,
        platform=platform,
        port=port,
    )


def create_ip_based_config(
    ips: list[str],
    platform: str,
    base_config: NetworkConfig,
    device_type: str | None = None,
    port: int | None = None,
) -> NetworkConfig:
    """
    Create a NetworkConfig with devices based on IP addresses.

    Parameters
    ----------
    ips : list[str]
        List of IP addresses
    platform : str
        Scrapli platform identifier
    base_config : NetworkConfig
        Base configuration to copy general settings from
    device_type : str | None
        Device type, defaults to platform if not provided
    port : int | None
        SSH port, defaults to 22 if not provided

    Returns
    -------
    NetworkConfig
        New configuration with IP-based devices
    """
    # Create device configs for each IP
    ip_devices: dict[str, DeviceConfig] = {}

    for ip in ips:
        # Use IP as device name (replace dots with dashes for valid names)
        device_name = f"ip_{ip.replace('.', '_')}"
        ip_devices[device_name] = create_ip_device_config(
            ip, platform, device_type, port
        )

    # Create new config with IP devices combined with existing devices
    combined_devices: dict[str, DeviceConfig] = {}
    if base_config.devices:
        combined_devices.update(base_config.devices)
    combined_devices.update(ip_devices)

    # Create new NetworkConfig with combined devices
    config_dict = base_config.model_dump()
    config_dict["devices"] = combined_devices

    return NetworkConfig.model_validate(config_dict)


def get_supported_platforms() -> dict[str, str]:
    """
    Get supported Scrapli platforms with descriptions.

    Returns
    -------
    dict[str, str]
        Mapping of platform names to descriptions
    """
    return {
        "mikrotik_routeros": "MikroTik RouterOS",
        "cisco_iosxe": "Cisco IOS-XE",
        "cisco_iosxr": "Cisco IOS-XR",
        "cisco_nxos": "Cisco NX-OS",
        "juniper_junos": "Juniper JunOS",
        "arista_eos": "Arista EOS",
        "linux": "Linux SSH",
    }


def validate_platform(platform: str) -> bool:
    """
    Validate if a platform is supported.

    Parameters
    ----------
    platform : str
        Platform identifier to validate

    Returns
    -------
    bool
        True if platform is supported
    """
    return platform in get_supported_platforms()
