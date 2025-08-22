# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Credential resolution and management."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from network_toolkit.config import DeviceConfig, NetworkConfig


class CredentialResolver:
    """
    Centralized credential resolution with clear precedence chain.

    Precedence order:
    1. Function parameters (interactive override)
    2. Device configuration
    3. Device-specific environment variables
    4. Group-level credentials (config and environment)
    5. Default environment variables
    """

    def __init__(self, config: NetworkConfig) -> None:
        """Initialize with network configuration."""
        self.config = config

    def resolve_credentials(
        self,
        device_name: str,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> tuple[str, str]:
        """
        Resolve credentials for a device following precedence chain.

        Parameters
        ----------
        device_name : str
            Name of the device
        username_override : str | None
            Interactive username override
        password_override : str | None
            Interactive password override

        Returns
        -------
        tuple[str, str]
            Resolved (username, password) tuple

        Raises
        ------
        ValueError
            If device not found or credentials cannot be resolved
        """
        if not self.config.devices or device_name not in self.config.devices:
            msg = f"Device '{device_name}' not found in configuration"
            raise ValueError(msg)

        device = self.config.devices[device_name]

        # Resolve username
        username = self._resolve_username(device_name, device, username_override)

        # Resolve password
        password = self._resolve_password(device_name, device, password_override)

        return username, password

    def _resolve_username(
        self,
        device_name: str,
        device: DeviceConfig,
        override: str | None = None,
    ) -> str:
        """Resolve username following precedence chain."""
        # 1. Function parameter override
        if override:
            return override

        # 2. Device configuration
        if device.user:
            return device.user

        # 3. Device-specific environment variable
        device_env_user = os.getenv(f"NW_USER_{device_name.upper().replace('-', '_')}")
        if device_env_user:
            return device_env_user

        # 4. Group-level credentials
        group_user, _ = self.config.get_group_credentials(device_name)
        if group_user:
            return group_user

        # 5. Default environment variable
        return self.config.general.default_user

    def _resolve_password(
        self,
        device_name: str,
        device: DeviceConfig,
        override: str | None = None,
    ) -> str:
        """Resolve password following precedence chain."""
        # 1. Function parameter override
        if override:
            return override

        # 2. Device configuration
        if device.password:
            return device.password

        # 3. Device-specific environment variable
        device_env_password = os.getenv(
            f"NW_PASSWORD_{device_name.upper().replace('-', '_')}"
        )
        if device_env_password:
            return device_env_password

        # 4. Group-level credentials
        _, group_password = self.config.get_group_credentials(device_name)
        if group_password:
            return group_password

        # 5. Default environment variable
        return self.config.general.default_password


class EnvironmentCredentialManager:
    """
    Centralized environment variable credential management.

    Handles the NW_ prefix convention and target-specific lookups.
    """

    @staticmethod
    def get_credential(
        target_name: str | None = None,
        credential_type: str = "user",
    ) -> str | None:
        """
        Get credentials from environment variables with NW_ prefix.

        Parameters
        ----------
        target_name : str | None
            Name of the device or group (will be converted to uppercase)
        credential_type : str
            Type of credential: "user" or "password"

        Returns
        -------
        str | None
            The credential value or None if not found
        """
        credential_type = credential_type.upper()

        # Try target-specific credential first
        if target_name:
            target_env_var = (
                f"NW_{credential_type}_{target_name.upper().replace('-', '_')}"
            )
            value = os.getenv(target_env_var)
            if value:
                return value

        # Fall back to default credential
        default_env_var = f"NW_{credential_type}_DEFAULT"
        return os.getenv(default_env_var)

    @staticmethod
    def get_device_specific(device_name: str, credential_type: str) -> str | None:
        """Get device-specific environment variable without fallback."""
        credential_type = credential_type.upper()
        env_var = f"NW_{credential_type}_{device_name.upper().replace('-', '_')}"
        return os.getenv(env_var)

    @staticmethod
    def get_group_specific(group_name: str, credential_type: str) -> str | None:
        """Get group-specific environment variable without fallback."""
        credential_type = credential_type.upper()
        env_var = f"NW_{credential_type}_{group_name.upper().replace('-', '_')}"
        return os.getenv(env_var)

    @staticmethod
    def get_default(credential_type: str) -> str | None:
        """Get default environment variable."""
        credential_type = credential_type.upper()
        env_var = f"NW_{credential_type}_DEFAULT"
        return os.getenv(env_var)


class ConnectionParameterBuilder:
    """
    Builder pattern for constructing device connection parameters.

    Separates the complex parameter building logic from NetworkConfig.
    """

    def __init__(self, config: NetworkConfig) -> None:
        """Initialize with network configuration."""
        self.config = config
        self.credential_resolver = CredentialResolver(config)

    def build_parameters(
        self,
        device_name: str,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Build complete connection parameters for a device.

        Parameters
        ----------
        device_name : str
            Name of the device
        username_override : str | None
            Override username
        password_override : str | None
            Override password

        Returns
        -------
        dict[str, Any]
            Complete connection parameters
        """
        if not self.config.devices or device_name not in self.config.devices:
            msg = f"Device '{device_name}' not found in configuration"
            raise ValueError(msg)

        device = self.config.devices[device_name]

        # Resolve credentials
        username, password = self.credential_resolver.resolve_credentials(
            device_name, username_override, password_override
        )

        # Build base parameters
        params = self._build_base_parameters(device, username, password)

        # Apply device overrides
        self._apply_device_overrides(params, device)

        return params

    def _build_base_parameters(
        self, device: DeviceConfig, username: str, password: str
    ) -> dict[str, Any]:
        """Build base connection parameters."""
        return {
            "host": device.host,
            "auth_username": username,
            "auth_password": password,
            "port": device.port or self.config.general.port,
            "timeout_socket": self.config.general.timeout,
            "timeout_transport": self.config.general.timeout,
            "transport": self.config.general.transport,
            # Prefer explicit platform, otherwise fall back to device_type
            # This keeps platform consistent with CLI/config-provided values
            "platform": device.platform or device.device_type,
        }

    def _apply_device_overrides(
        self, params: dict[str, Any], device: DeviceConfig
    ) -> None:
        """Apply device-specific overrides to parameters."""
        if not device.overrides:
            return

        if device.overrides.user:
            params["auth_username"] = device.overrides.user
        if device.overrides.password:
            params["auth_password"] = device.overrides.password
        if device.overrides.port:
            params["port"] = device.overrides.port
        if device.overrides.timeout:
            params["timeout_socket"] = device.overrides.timeout
            params["timeout_transport"] = device.overrides.timeout
        if device.overrides.transport:
            params["transport"] = device.overrides.transport
