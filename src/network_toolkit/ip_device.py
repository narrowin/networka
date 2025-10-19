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
    device_type: str,
    hardware_platform: str | None = None,
    port: int | None = None,
    transport_type: str | None = None,
) -> DeviceConfig:
    """
    Create a DeviceConfig from an IP address and device type.

    Parameters
    ----------
    ip : str
        IP address of the device
    device_type : str
        Network driver type identifier (e.g., 'mikrotik_routeros', 'cisco_iosxe')
        This determines which Scrapli/transport driver to use for connections.
        Must be a valid SupportedDeviceType.
    hardware_platform : str | None
        Hardware platform architecture (e.g., 'x86', 'arm', 'tile')
        Used for firmware operations. Optional.
    port : int | None
        SSH port, defaults to 22 if not provided
    transport_type : str | None
        Transport type (currently only 'scrapli' is supported)
        Defaults to configuration or 'scrapli'

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

    # Validate device_type against supported types
    from network_toolkit.config import get_supported_device_types

    if device_type not in get_supported_device_types():
        supported = ", ".join(sorted(get_supported_device_types()))
        msg = f"Unsupported device_type '{device_type}'. Supported types: {supported}"
        raise ValueError(msg)

    # Default port to 22 if not provided
    if port is None:
        port = 22

    return DeviceConfig(
        host=ip,
        description=f"Dynamic device at {ip}",
        device_type=device_type,  # Validated above
        platform=hardware_platform,
        port=port,
        transport_type=transport_type,
    )


def create_ip_based_config(
    ips: list[str],
    device_type: str,
    base_config: NetworkConfig,
    hardware_platform: str | None = None,
    port: int | None = None,
    transport_type: str | None = None,
) -> NetworkConfig:
    """
    Create a NetworkConfig with IP-based device configurations.

    Parameters
    ----------
    ips : list[str]
        List of IP addresses to create device configurations for
    device_type : str
        Network driver type for all IP devices (e.g., 'mikrotik_routeros')
    base_config : NetworkConfig
        Base configuration to extend with IP devices
    hardware_platform : str | None
        Hardware platform architecture for all IP devices (e.g., 'x86', 'arm')
    port : int | None
        SSH port for all IP devices, defaults to 22
    transport_type : str | None
        Transport type for all IP devices (currently only 'scrapli' is supported)

    Returns
    -------
    NetworkConfig
        Enhanced configuration including IP-based devices
    """
    ip_devices: dict[str, DeviceConfig] = {}

    for ip in ips:
        # Create a device name from the IP
        device_name = f"ip_{ip.replace('.', '_').replace(':', '_')}"
        ip_devices[device_name] = create_ip_device_config(
            ip, device_type, hardware_platform, port, transport_type
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


def get_supported_device_types() -> dict[str, str]:
    """
    Get supported device types with descriptions.

    Returns
    -------
    dict[str, str]
        Mapping of device type names to descriptions
    """
    from network_toolkit.config import get_supported_device_types

    # Map device types to human-readable descriptions
    descriptions = {
        "mikrotik_routeros": "MikroTik RouterOS",
        "cisco_iosxe": "Cisco IOS-XE",
        "cisco_ios": "Cisco IOS",
        "cisco_iosxr": "Cisco IOS-XR",
        "cisco_nxos": "Cisco NX-OS",
        "juniper_junos": "Juniper JunOS",
        "arista_eos": "Arista EOS",
        "nokia_srlinux": "Nokia SR Linux",
        "linux": "Linux SSH",
        "generic": "Generic SSH",
    }

    # Only return descriptions for supported device types
    supported_types = get_supported_device_types()
    return {
        dt: descriptions.get(dt, dt) for dt in supported_types if dt in descriptions
    }


# Backward compatibility alias
get_supported_platforms = get_supported_device_types


def validate_platform(device_type: str) -> bool:
    """
    Validate if a device type is supported.

    Note: This function name is maintained for backward compatibility,
    but it actually validates device types (network drivers), not hardware platforms.

    Parameters
    ----------
    device_type : str
        Device type identifier to validate

    Returns
    -------
    bool
        True if device type is supported
    """
    return device_type in get_supported_device_types()
