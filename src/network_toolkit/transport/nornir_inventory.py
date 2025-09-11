"""Nornir inventory builder from NetworkConfig."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nornir.core.inventory import Inventory

from network_toolkit.config import NetworkConfig


def build_nornir_inventory(config: NetworkConfig) -> Inventory:
    """Build Nornir inventory from NetworkConfig.

    Parameters
    ----------
    config : NetworkConfig
        The network configuration containing device definitions

    Returns
    -------
    Inventory
        Nornir inventory object

    Raises
    ------
    ImportError
        If Nornir is not installed
    """
    try:
        from nornir.core.inventory import (
            ConnectionOptions,
            Defaults,
            Groups,
            Host,
            Hosts,
            Inventory,
        )
    except ImportError as e:
        error_msg = (
            "Nornir package required for Nornir transport. "
            "Install with: pip install nornir"
        )
        raise ImportError(error_msg) from e

    if not config.devices:
        # Return empty inventory if no devices
        return Inventory(hosts=Hosts(), groups=Groups(), defaults=Defaults())

    hosts = Hosts()

    for device_name, device_config in config.devices.items():
        # Skip devices that don't use nornir transport
        transport_type = getattr(device_config, "transport_type", "scrapli")
        if transport_type != "nornir_netmiko":
            continue

        # Get credentials for this device
        user_env_var = f"NW_USER_{device_name.upper().replace('-', '_')}"
        password_env_var = f"NW_PASSWORD_{device_name.upper().replace('-', '_')}"
        username = os.getenv(user_env_var) or os.getenv("NW_USER_DEFAULT", "admin")
        password = os.getenv(password_env_var) or os.getenv("NW_PASSWORD_DEFAULT", "")

        if not password:
            # Skip devices without proper credentials
            continue

        # Map device type to Netmiko platform
        netmiko_platform = _map_to_netmiko_platform(device_config.device_type)

        # Create connection options
        netmiko_options = ConnectionOptions(
            extras={
                "device_type": netmiko_platform,
                "timeout": getattr(device_config, "timeout", 30),
                "global_delay_factor": 1,
                "use_keys": False,
                "key_file": None,
            }
        )

        # Create host with all necessary parameters
        host = Host(
            name=device_name,
            hostname=device_config.host,
            username=username,
            password=password,
            port=device_config.port or 22,
            platform=netmiko_platform,
            connection_options={"netmiko": netmiko_options},
            # Store additional device metadata
            data={
                "description": device_config.description,
                "device_type": device_config.device_type,
                "model": device_config.model,
                "location": device_config.location,
                "tags": device_config.tags or [],
                "original_config": device_config.model_dump(),
            },
        )

        hosts[device_name] = host

    # Create empty groups for now - could be extended to map device_groups
    groups = Groups()

    # Create defaults
    default_netmiko_options = ConnectionOptions(
        extras={
            "timeout": config.general.timeout,
            "global_delay_factor": 1,
            "use_keys": False,
        }
    )

    defaults = Defaults(connection_options={"netmiko": default_netmiko_options})

    return Inventory(hosts=hosts, groups=groups, defaults=defaults)


def _map_to_netmiko_platform(device_type: str) -> str:
    """Map internal device types to Netmiko platform names.

    Parameters
    ----------
    device_type : str
        Internal device type identifier

    Returns
    -------
    str
        Netmiko platform name
    """
    platform_mapping = {
        # MikroTik
        "mikrotik_routeros": "mikrotik_routeros",
        # Cisco
        "cisco_iosxe": "cisco_xe",
        "cisco_ios": "cisco_ios",
        "cisco_nxos": "cisco_nxos",
        "cisco_iosxr": "cisco_xr",
        # Arista
        "arista_eos": "arista_eos",
        # Juniper
        "juniper_junos": "juniper_junos",
        # Others
        "linux": "linux",
        "generic": "terminal_server",
    }

    return platform_mapping.get(device_type, device_type)


def get_supported_nornir_platforms() -> dict[str, str]:
    """Get mapping of supported platforms for Nornir transport.

    Returns
    -------
    dict[str, str]
        Mapping of internal device_type to description
    """
    return {
        "mikrotik_routeros": "MikroTik RouterOS",
        "cisco_iosxe": "Cisco IOS-XE",
        "cisco_ios": "Cisco IOS",
        "cisco_nxos": "Cisco NX-OS",
        "cisco_iosxr": "Cisco IOS-XR",
        "arista_eos": "Arista EOS",
        "juniper_junos": "Juniper JunOS",
        "linux": "Linux SSH",
    }
