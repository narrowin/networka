# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Centralized device and group resolution utilities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from network_toolkit.ip_device import (
    create_ip_based_config,
    extract_ips_from_target,
    is_ip_list,
)

if TYPE_CHECKING:
    from network_toolkit.config import NetworkConfig


class DeviceResolver:
    """Centralized device and group resolution logic."""

    def __init__(
        self,
        config: NetworkConfig,
        platform: str | None = None,
        port: int | None = None,
        transport_type: str | None = None,
    ) -> None:
        """Initialize resolver with configuration.

        Parameters
        ----------
        config : NetworkConfig
            Network configuration containing devices and groups
        platform : str | None
            Platform type to use for IP-based devices
        port : int | None
            Port to use for IP-based devices
        transport_type : str | None
            Transport type to use for IP-based devices
        """
        self.config = config
        self.platform = platform
        self.port = port
        self.transport_type = transport_type
        self._ip_config_cache: NetworkConfig | None = None

    def _get_ip_enhanced_config(self, target_expr: str) -> NetworkConfig:
        """Get config enhanced with IP-based devices if needed."""
        if not is_ip_list(target_expr):
            return self.config

        if self.platform is None:
            msg = "Platform must be specified when using IP addresses"
            raise ValueError(msg)

        # Cache the enhanced config to avoid recreating it
        if self._ip_config_cache is None:
            ips = extract_ips_from_target(target_expr)
            self._ip_config_cache = create_ip_based_config(
                ips,
                self.platform,
                self.config,
                port=self.port,
                transport_type=self.transport_type,
            )

        return self._ip_config_cache

    def resolve_targets(self, target_expr: str) -> tuple[list[str], list[str]]:
        """Resolve a target expression to concrete device names.

        Parameters
        ----------
        target_expr : str
            Comma-separated list of device names, group names, or IP addresses

        Returns
        -------
        tuple[list[str], list[str]]
            Tuple of (resolved_devices, unknown_targets)
        """
        # Handle IP addresses
        if is_ip_list(target_expr):
            if self.platform is None:
                msg = "Platform must be specified when using IP addresses"
                raise ValueError(msg)
            ips = extract_ips_from_target(target_expr)
            ip_device_names = [f"ip_{ip.replace('.', '_')}" for ip in ips]
            # Ensure the config is enhanced with IP devices
            self._get_ip_enhanced_config(target_expr)
            return ip_device_names, []

        # Use enhanced config for resolution
        config = self._get_ip_enhanced_config(target_expr)
        requested = [t.strip() for t in target_expr.split(",") if t.strip()]
        devices: list[str] = []
        unknowns: list[str] = []

        def _add_device(name: str) -> None:
            if name not in devices:
                devices.append(name)

        for name in requested:
            if config.devices and name in config.devices:
                _add_device(name)
                continue
            if config.device_groups and name in config.device_groups:
                try:
                    for member in config.get_group_members(name):
                        _add_device(member)
                    continue
                except Exception as exc:
                    # Group exists but has no valid members - log and skip it
                    logging.warning(f"Failed to resolve group {name}: {exc}")
                    continue
            unknowns.append(name)

        return devices, unknowns

    @property
    def effective_config(self) -> NetworkConfig:
        """Get the effective config (enhanced with IP devices if any)."""
        return self._ip_config_cache or self.config

    def is_device(self, name: str) -> bool:
        """Check if name is a valid device.

        Parameters
        ----------
        name : str
            Device name to check

        Returns
        -------
        bool
            True if name is a valid device
        """
        config = self.effective_config
        return bool(config.devices and name in config.devices)

    def is_group(self, name: str) -> bool:
        """Check if name is a valid group.

        Parameters
        ----------
        name : str
            Group name to check

        Returns
        -------
        bool
            True if name is a valid group
        """
        config = self.effective_config
        return bool(config.device_groups and name in config.device_groups)

    def get_group_members(self, group_name: str) -> list[str]:
        """Get members of a group.

        Parameters
        ----------
        group_name : str
            Name of the group

        Returns
        -------
        list[str]
            List of device names in the group

        Raises
        ------
        ValueError
            If group does not exist
        """
        if not self.is_group(group_name):
            msg = f"Group '{group_name}' does not exist"
            raise ValueError(msg)

        try:
            return self.effective_config.get_group_members(group_name)
        except Exception as e:
            msg = f"Failed to get members for group '{group_name}': {e}"
            raise ValueError(msg) from e

    def validate_target(self, target: str) -> tuple[bool, str]:
        """Validate a single target (device or group).

        Parameters
        ----------
        target : str
            Target name to validate

        Returns
        -------
        tuple[bool, str]
            Tuple of (is_valid, target_type) where target_type is
            'device', 'group', or 'unknown'
        """
        if self.is_device(target):
            return True, "device"
        elif self.is_group(target):
            return True, "group"
        else:
            return False, "unknown"
