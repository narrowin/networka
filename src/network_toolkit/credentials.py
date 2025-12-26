# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Credential resolution and management."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from network_toolkit.introspection import LoaderType

if TYPE_CHECKING:
    from network_toolkit.config import DeviceConfig, NetworkConfig


# module logger
logger = logging.getLogger(__name__)


@dataclass
class CredentialSource:
    """Describes where a credential value came from."""

    value: str
    loader: LoaderType
    identifier: str | None = None

    def format(self) -> str:
        """Format the source as a human-readable string."""
        if self.loader == LoaderType.ENV_VAR:
            return f"env: {self.identifier}" if self.identifier else "env"
        elif self.loader == LoaderType.GROUP:
            return f"group: {self.identifier}" if self.identifier else "group"
        elif self.loader == LoaderType.CONFIG_FILE:
            return f"config: {self.identifier}" if self.identifier else "config"
        elif self.loader == LoaderType.PYDANTIC_DEFAULT:
            return "default"
        elif self.loader == LoaderType.CLI:
            return "cli"
        elif self.loader == LoaderType.INTERACTIVE:
            return "interactive"
        return str(self.loader.value)


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

    def resolve_credentials_with_source(
        self,
        device_name: str,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> tuple[tuple[str, str], tuple[CredentialSource, CredentialSource]]:
        """
        Resolve credentials with source tracking.

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
        tuple[tuple[str, str], tuple[CredentialSource, CredentialSource]]
            ((username, password), (username_source, password_source))
        """
        if not self.config.devices or device_name not in self.config.devices:
            msg = f"Device '{device_name}' not found in configuration"
            raise ValueError(msg)

        device = self.config.devices[device_name]

        username, user_source = self._resolve_username_with_source(
            device_name, device, username_override
        )
        password, pass_source = self._resolve_password_with_source(
            device_name, device, password_override
        )

        return (username, password), (user_source, pass_source)

    def _resolve_username_with_source(
        self,
        device_name: str,
        device: DeviceConfig,
        override: str | None = None,
    ) -> tuple[str, CredentialSource]:
        """Resolve username with source tracking."""
        # 1. Function parameter override
        if override:
            return override, CredentialSource(
                value=override, loader=LoaderType.INTERACTIVE, identifier="cli"
            )

        # 2. Device configuration
        if device.user:
            source_path = getattr(device, "_source_path", None)
            identifier = str(source_path) if source_path else "device config"
            return device.user, CredentialSource(
                value=device.user, loader=LoaderType.CONFIG_FILE, identifier=identifier
            )

        # 3. Device-specific environment variable
        env_var_name = f"NW_USER_{device_name.upper().replace('-', '_')}"
        device_env_user = os.getenv(env_var_name)
        if device_env_user:
            return device_env_user, CredentialSource(
                value=device_env_user,
                loader=LoaderType.ENV_VAR,
                identifier=env_var_name,
            )

        # 4. Group-level credentials (with source tracking)
        group_user, _, group_name = self._get_group_credentials_with_source(
            device_name, "user"
        )
        if group_user and group_name:
            return group_user, CredentialSource(
                value=group_user, loader=LoaderType.GROUP, identifier=group_name
            )

        # 5. Default environment variable
        default_user = self.config.general.default_user
        return default_user, CredentialSource(
            value=default_user, loader=LoaderType.ENV_VAR, identifier="NW_USER_DEFAULT"
        )

    def _resolve_password_with_source(
        self,
        device_name: str,
        device: DeviceConfig,
        override: str | None = None,
    ) -> tuple[str, CredentialSource]:
        """Resolve password with source tracking."""
        # 1. Function parameter override
        if override:
            return override, CredentialSource(
                value=override, loader=LoaderType.INTERACTIVE, identifier="cli"
            )

        # 2. Device configuration
        if device.password:
            source_path = getattr(device, "_source_path", None)
            identifier = str(source_path) if source_path else "device config"
            return device.password, CredentialSource(
                value=device.password,
                loader=LoaderType.CONFIG_FILE,
                identifier=identifier,
            )

        # 3. Device-specific environment variable
        env_var_name = f"NW_PASSWORD_{device_name.upper().replace('-', '_')}"
        device_env_password = os.getenv(env_var_name)
        if device_env_password:
            return device_env_password, CredentialSource(
                value=device_env_password,
                loader=LoaderType.ENV_VAR,
                identifier=env_var_name,
            )

        # 4. Group-level credentials (with source tracking)
        _, group_password, group_name = self._get_group_credentials_with_source(
            device_name, "password"
        )
        if group_password and group_name:
            return group_password, CredentialSource(
                value=group_password, loader=LoaderType.GROUP, identifier=group_name
            )

        # 5. Default environment variable
        default_password = self.config.general.default_password
        return default_password, CredentialSource(
            value=default_password,
            loader=LoaderType.ENV_VAR,
            identifier="NW_PASSWORD_DEFAULT",
        )

    def _get_group_credentials_with_source(
        self, device_name: str, credential_type: str
    ) -> tuple[str | None, str | None, str | None]:
        """
        Get group-level credentials with source tracking.

        Returns
        -------
        tuple[str | None, str | None, str | None]
            (user, password, group_name) - group_name indicates which group provided creds
        """
        device_groups = self.config.get_device_groups(device_name)

        for group_name in device_groups:
            group = (
                self.config.device_groups.get(group_name)
                if self.config.device_groups
                else None
            )
            if group and group.credentials:
                # Check for explicit credentials in group config
                if credential_type == "user" and group.credentials.user:
                    return group.credentials.user, None, group_name
                if credential_type == "password" and group.credentials.password:
                    return None, group.credentials.password, group_name

                # Check for environment variables for this group
                group_user = EnvironmentCredentialManager.get_group_specific(
                    group_name, "user"
                )
                group_password = EnvironmentCredentialManager.get_group_specific(
                    group_name, "password"
                )
                if credential_type == "user" and group_user:
                    return group_user, None, f"{group_name} (env)"
                if credential_type == "password" and group_password:
                    return None, group_password, f"{group_name} (env)"

        return None, None, None


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
        """Build base connection parameters.

        Uses device_type for Scrapli platform parameter since device_type
        defines the network driver/protocol, while platform defines hardware architecture.
        """
        # Map internal device_type to Scrapli platform names
        # Scrapli does not have 'cisco_ios' - it uses 'cisco_iosxe' for both IOS and IOS-XE
        scrapli_platform = self._map_to_scrapli_platform(device.device_type)

        logger.debug(
            "credentials: device_type=%s scrapli_platform=%s",
            device.device_type,
            scrapli_platform,
        )

        params: dict[str, Any] = {
            "host": device.host,
            "auth_username": username,
            "auth_password": password,
            "port": device.port or self.config.general.port,
            "timeout_socket": self.config.general.timeout,
            "timeout_transport": self.config.general.timeout,
            "transport": self.config.general.transport,
            "ssh_config_file": self.config.general.ssh_config_file,
        }

        # Only add platform if it's not None (for generic/linux connections)
        if scrapli_platform is not None:
            # Use mapped platform for Scrapli - this determines the network driver
            # The platform field is reserved for hardware architecture (x86, arm, etc.)
            params["platform"] = scrapli_platform
            logger.debug("credentials: added platform=%s to params", scrapli_platform)
        else:
            # For generic/linux connections, use GenericDriver with suitable prompt pattern
            # GenericDriver default is: r"^\S{0,48}[#>$~@:\]]\s*$"
            # We extend this for Linux which can have longer hostnames/paths
            # Pattern matches: user@host:~$, root@host#, user@host:~/path$, etc.
            # Scrapli uses multiline + case insensitive regex flags
            params["comms_prompt_pattern"] = r"^\S+[\$#]\s*$"
            # Increase timeout for generic connections as prompt detection may take longer
            params["timeout_ops"] = 60
            logger.debug(
                "credentials: not adding platform; set comms_prompt_pattern and timeout_ops=60 for generic/linux"
            )

        logger.debug("credentials: final params keys: %s", list(params.keys()))
        logger.debug("credentials: 'platform' in params: %s", "platform" in params)
        if "platform" in params:
            logger.debug("credentials: params['platform'] = %s", params["platform"])
        if "comms_prompt_pattern" in params:
            logger.debug(
                "credentials: params['comms_prompt_pattern'] = %s",
                params["comms_prompt_pattern"],
            )
        return params

    def _map_to_scrapli_platform(self, device_type: str) -> str | None:
        """Map internal device_type to Scrapli platform name.

        Scrapli core drivers use specific platform names that may differ
        from our internal device_type names. This function handles the mapping.

        Parameters
        ----------
        device_type : str
            Internal device type identifier

        Returns
        -------
        str | None
            Scrapli platform name, or None for generic/linux connections
        """
        # Scrapli does not have 'cisco_ios' - use 'cisco_iosxe' for both IOS and IOS-XE
        platform_mapping = {
            "cisco_ios": "cisco_iosxe",
            # For Linux/generic SSH, don't pass a platform - use GenericDriver
            "linux": None,
            "generic": None,
        }
        return platform_mapping.get(device_type, device_type)

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
