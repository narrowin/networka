# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Configuration management for network toolkit."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

from network_toolkit.exceptions import NetworkToolkitError


def get_env_credential(
    device_name: str | None = None, credential_type: str = "user"
) -> str | None:
    """
    Get credentials from environment variables.

    Supports both device-specific and default credentials:
    - Device-specific: NT_{DEVICE_NAME}_{USER|PASSWORD}
    - Default: NT_DEFAULT_{USER|PASSWORD}

    Parameters
    ----------
    device_name : str | None
        Name of the device (will be converted to uppercase for env var lookup)
    credential_type : str
        Type of credential: "user" or "password"

    Returns
    -------
    str | None
        The credential value or None if not found
    """
    credential_type = credential_type.upper()

    # Try device-specific credential first
    if device_name:
        device_env_var = f"NT_{device_name.upper().replace('-', '_')}_{credential_type}"
        value = os.getenv(device_env_var)
        if value:
            return value

    # Fall back to default credential
    default_env_var = f"NT_DEFAULT_{credential_type}"
    return os.getenv(default_env_var)


class GeneralConfig(BaseModel):
    """General configuration settings."""

    # Directory paths
    firmware_dir: str = "/tmp/firmware"
    backup_dir: str = "/tmp/backups"
    logs_dir: str = "/tmp/logs"
    results_dir: str = "/tmp/results"

    # Default connection settings (credentials now come from environment variables)
    transport: str = "ssh"
    port: int = 22
    timeout: int = 30
    default_transport_type: str = "scrapli"

    # Connection retry settings
    connection_retries: int = 3
    retry_delay: int = 5

    # File transfer settings
    transfer_timeout: int = 300
    verify_checksums: bool = True

    # Command execution settings
    command_timeout: int = 60
    enable_logging: bool = True
    log_level: str = "INFO"

    # Backup retention policy
    backup_retention_days: int = 30
    max_backups_per_device: int = 10

    # Results storage configuration
    store_results: bool = False
    results_format: str = "txt"
    results_include_timestamp: bool = True
    results_include_command: bool = True

    @property
    def default_user(self) -> str:
        """Get default username from environment variable."""
        user = get_env_credential(credential_type="user")
        if not user:
            msg = (
                "Default username not found in environment. "
                "Please set NT_DEFAULT_USER environment variable."
            )
            raise ValueError(msg)
        return user

    @property
    def default_password(self) -> str:
        """Get default password from environment variable."""
        password = get_env_credential(credential_type="password")
        if not password:
            msg = (
                "Default password not found in environment. "
                "Please set NT_DEFAULT_PASSWORD environment variable."
            )
            raise ValueError(msg)
        return password

    @field_validator("results_format")
    @classmethod
    def validate_results_format(cls, v: str) -> str:
        """Validate results format is supported."""
        if v.lower() not in ["txt", "json", "yaml"]:
            msg = "results_format must be one of: txt, json, yaml"
            raise ValueError(msg)
        return v.lower()

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Validate transport is supported."""
        if v.lower() not in ["ssh", "telnet"]:
            msg = "transport must be either 'ssh' or 'telnet'"
            raise ValueError(msg)
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is supported."""
        if v.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            msg = "log_level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            raise ValueError(msg)
        return v.upper()


class DeviceOverrides(BaseModel):
    """Device-specific configuration overrides."""

    user: str | None = None
    password: str | None = None
    port: int | None = None
    timeout: int | None = None
    transport: str | None = None
    command_timeout: int | None = None
    transfer_timeout: int | None = None


class DeviceConfig(BaseModel):
    """Configuration for a single network device."""

    host: str
    description: str | None = None
    device_type: str = "mikrotik_routeros"
    model: str | None = None
    platform: str | None = None
    location: str | None = None
    user: str | None = None
    password: str | None = None
    port: int | None = None
    transport_type: str | None = None
    tags: list[str] | None = None
    overrides: DeviceOverrides | None = None
    command_sequences: dict[str, list[str]] | None = None


class DeviceGroup(BaseModel):
    """Configuration for a device group."""

    description: str
    members: list[str] | None = None
    match_tags: list[str] | None = None


class VendorPlatformConfig(BaseModel):
    """Configuration for vendor platform support."""

    description: str
    sequence_path: str
    default_files: list[str] = ["common.yml"]


class VendorSequence(BaseModel):
    """Vendor-specific command sequence definition."""

    description: str
    category: str | None = None
    timeout: int | None = None
    device_types: list[str] | None = None
    commands: list[str]


class CommandSequence(BaseModel):
    """Global command sequence definition."""

    description: str
    commands: list[str]
    tags: list[str] | None = None
    file_operations: dict[str, Any] | None = None


class CommandSequenceGroup(BaseModel):
    """Command sequence group definition."""

    description: str
    match_tags: list[str]


class FileOperationConfig(BaseModel):
    """File operation configuration."""

    local_path: str | None = None
    remote_path: str | None = None
    verify_checksum: bool | None = None
    backup_before_upgrade: bool | None = None
    remote_files: list[str] | None = None
    compress: bool | None = None
    file_pattern: str | None = None


class NetworkConfig(BaseModel):
    """Complete network toolkit configuration."""

    general: GeneralConfig = GeneralConfig()
    devices: dict[str, DeviceConfig] | None = None
    device_groups: dict[str, DeviceGroup] | None = None
    global_command_sequences: dict[str, CommandSequence] | None = None
    command_sequence_groups: dict[str, CommandSequenceGroup] | None = None
    file_operations: dict[str, FileOperationConfig] | None = None

    # Multi-vendor support
    vendor_platforms: dict[str, VendorPlatformConfig] | None = None
    vendor_sequences: dict[str, dict[str, VendorSequence]] | None = None

    def get_device_connection_params(
        self,
        device_name: str,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Get connection parameters for a device.

        Parameters
        ----------
        device_name : str
            Name of the device to get parameters for
        username_override : str | None
            Override username (takes precedence over all other sources)
        password_override : str | None
            Override password (takes precedence over all other sources)

        Returns
        -------
        dict[str, Any]
            Connection parameters dictionary

        Raises
        ------
        ValueError
            If device is not found in configuration
        """
        if not self.devices or device_name not in self.devices:
            msg = f"Device '{device_name}' not found in configuration"
            raise ValueError(msg)

        device = self.devices[device_name]

        # Get credentials with override priority:
        # 1. Function parameters (interactive override)
        # 2. Device configuration
        # 3. Environment variables (device-specific)
        # 4. Default environment variables
        username = (
            username_override
            or device.user
            or get_env_credential(device_name, "user")
            or self.general.default_user
        )
        password = (
            password_override
            or device.password
            or get_env_credential(device_name, "password")
            or self.general.default_password
        )

        # Start with general config defaults
        params = {
            "host": device.host,
            "auth_username": username,
            "auth_password": password,
            "port": device.port or self.general.port,
            "timeout_socket": self.general.timeout,
            "timeout_transport": self.general.timeout,
            "transport": self.general.transport,
            "platform": device.platform or "mikrotik_routeros",
        }

        # Apply device-specific overrides
        if device.overrides:
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

        return params

    def get_group_members(self, group_name: str) -> list[str]:
        """Get list of device names in a group."""
        if not self.device_groups or group_name not in self.device_groups:
            msg = f"Device group '{group_name}' not found in configuration"
            raise NetworkToolkitError(msg, details={"group": group_name})

        group = self.device_groups[group_name]
        members = []

        # Direct members
        if group.members:
            members.extend(
                [m for m in group.members if self.devices and m in self.devices]
            )

        # Tag-based members
        if group.match_tags and self.devices:
            for device_name, device in self.devices.items():
                if device.tags and any(tag in device.tags for tag in group.match_tags):
                    if device_name not in members:
                        members.append(device_name)

        return members

    def get_transport_type(self, device_name: str) -> str:
        """
        Get the transport type for a device.

        Parameters
        ----------
        device_name : str
            Name of the device

        Returns
        -------
        str
            Transport type ('scrapli' or 'nornir_netmiko')
        """
        if not self.devices or device_name not in self.devices:
            return self.general.default_transport_type

        device = self.devices[device_name]
        return device.transport_type or self.general.default_transport_type

    def get_command_sequences_by_tags(
        self, tags: list[str]
    ) -> dict[str, CommandSequence]:
        """
        Get command sequences that match any of the specified tags.

        Parameters
        ----------
        tags : list[str]
            List of tags to match against

        Returns
        -------
        dict[str, CommandSequence]
            Dictionary of sequence names to CommandSequence objects that match the tags
        """
        if not self.global_command_sequences:
            return {}

        matching_sequences = {}
        for sequence_name, sequence in self.global_command_sequences.items():
            if sequence.tags and any(tag in sequence.tags for tag in tags):
                matching_sequences[sequence_name] = sequence

        return matching_sequences

    def list_command_sequence_groups(self) -> dict[str, CommandSequenceGroup]:
        """
        List all available command sequence groups.

        Returns
        -------
        dict[str, CommandSequenceGroup]
            Dictionary of group names to CommandSequenceGroup objects
        """
        return self.command_sequence_groups or {}

    def get_command_sequences_by_group(
        self, group_name: str
    ) -> dict[str, CommandSequence]:
        """
        Get command sequences that match a specific group's tags.

        Parameters
        ----------
        group_name : str
            Name of the command sequence group

        Returns
        -------
        dict[str, CommandSequence]
            Dictionary of sequence names to CommandSequence objects that match the group's tags

        Raises
        ------
        ValueError
            If the group doesn't exist
        """
        if (
            not self.command_sequence_groups
            or group_name not in self.command_sequence_groups
        ):
            msg = f"Command sequence group '{group_name}' not found in configuration"
            raise ValueError(msg)

        group = self.command_sequence_groups[group_name]
        return self.get_command_sequences_by_tags(group.match_tags)

    # --- New unified sequence helpers ---
    def get_all_sequences(self) -> dict[str, dict[str, Any]]:
        """Return all available sequences from global and device-specific configs.

        Returns
        -------
        dict[str, dict]
            Mapping of sequence name -> info dict with keys:
            - commands: list[str]
            - origin: "global" | "device"
            - sources: list[str] (device names if origin == "device", or ["global"])
            - description: str | None (only for global sequences)
        """
        sequences: dict[str, dict[str, Any]] = {}

        # Add global sequences first (these take precedence)
        if self.global_command_sequences:
            for name, seq in self.global_command_sequences.items():
                sequences[name] = {
                    "commands": list(seq.commands),
                    "origin": "global",
                    "sources": ["global"],
                    "description": getattr(seq, "description", None),
                }

        # Add device-specific sequences if not already defined globally
        if self.devices:
            for dev_name, dev in self.devices.items():
                if not dev.command_sequences:
                    continue
                for name, commands in dev.command_sequences.items():
                    if name not in sequences:
                        sequences[name] = {
                            "commands": list(commands),
                            "origin": "device",
                            "sources": [dev_name],
                            "description": None,
                        }
                    elif sequences[name]["origin"] == "device":
                        # Track additional device sources for same-named sequence
                        sources = sequences[name].setdefault("sources", [])
                        if dev_name not in sources:
                            sources.append(dev_name)
        return sequences

    def resolve_sequence_commands(
        self, sequence_name: str, device_name: str | None = None
    ) -> list[str] | None:
        """Resolve commands for a sequence name from any origin.

        Parameters
        ----------
        sequence_name : str
            Name of the sequence to resolve
        device_name : str | None
            Device name to use for vendor-specific sequence resolution

        Returns
        -------
        list[str] | None
            List of commands for the sequence, or None if not found

        Resolution order:
        1. Global sequence definitions (highest priority)
        2. Vendor-specific sequences based on device's device_type
        3. Device-specific sequences (lowest priority)
        """
        # 1. Prefer global definition
        if (
            self.global_command_sequences
            and sequence_name in self.global_command_sequences
        ):
            return list(self.global_command_sequences[sequence_name].commands)

        # 2. Look for vendor-specific sequences
        if device_name and self.devices and device_name in self.devices:
            device = self.devices[device_name]
            vendor_commands = self._resolve_vendor_sequence(
                sequence_name, device.device_type
            )
            if vendor_commands:
                return vendor_commands

        # 3. Fall back to any device-defined sequence
        if self.devices:
            for dev in self.devices.values():
                if dev.command_sequences and sequence_name in dev.command_sequences:
                    return list(dev.command_sequences[sequence_name])
        return None

    def _resolve_vendor_sequence(
        self, sequence_name: str, device_type: str
    ) -> list[str] | None:
        """Resolve vendor-specific sequence commands.

        Parameters
        ----------
        sequence_name : str
            Name of the sequence to resolve
        device_type : str
            Device type (e.g., 'mikrotik_routeros', 'cisco_iosxe')

        Returns
        -------
        list[str] | None
            List of commands for the vendor-specific sequence, or None if not found
        """
        if (
            not self.vendor_sequences
            or device_type not in self.vendor_sequences
            or sequence_name not in self.vendor_sequences[device_type]
        ):
            return None

        vendor_sequence = self.vendor_sequences[device_type][sequence_name]
        return list(vendor_sequence.commands)


def load_config(config_path: str | Path) -> NetworkConfig:
    """
    Load and validate configuration from YAML file(s).

    Supports both:
    1. New modular config: config_path as directory containing config/, devices.yml,
       groups.yml, sequences.yml
    2. Legacy monolithic: config_path as single devices.yml file
    """
    config_path = Path(config_path)
    original_path = config_path  # Keep track of original user input

    # Check for new modular configuration structure
    if config_path.name in ["config", "config/"]:
        # Direct config directory path
        config_dir = config_path
        if not config_dir.exists():
            msg = f"Configuration directory not found: {config_dir}"
            raise FileNotFoundError(msg)
        return load_modular_config(config_dir)

    # If user provided an explicit file path that doesn't exist, fail immediately
    if not config_path.exists() and str(original_path) not in ["config", "devices.yml"]:
        # User specified an explicit path that doesn't exist
        msg = f"Configuration file not found: {config_path}"
        raise FileNotFoundError(msg)

    # Check if config_path is a directory or if config/ directory exists alongside it
    if config_path.is_dir():
        # Support directories that directly contain the modular files (config.yml, devices.yml, ...)
        direct_config_file = config_path / "config.yml"
        direct_devices_file = config_path / "devices.yml"
        if direct_config_file.exists() and direct_devices_file.exists():
            return load_modular_config(config_path)
        # Also support nested "config/" directory inside the provided directory
        config_dir = config_path / "config"
    else:
        config_dir = config_path.parent / "config"

    # Try modular config first (nested config/ next to provided path)
    if config_dir.exists() and config_dir.is_dir():
        return load_modular_config(config_dir)

    # Legacy monolithic config - if file exists, load it
    if config_path.exists():
        return load_legacy_config(config_path)

    # Only try fallback paths for default config names
    if str(original_path) in ["config", "devices.yml"]:
        possible_paths = [
            Path("config/config.yml"),  # Modular config
            Path("devices.yml"),  # Legacy config in root
        ]

        for path in possible_paths:
            if path.exists():
                if path.name == "config.yml" and path.parent.name == "config":
                    return load_modular_config(path.parent)
                else:
                    return load_legacy_config(path)

    # If we get here, nothing was found
    msg = f"Configuration file not found: {config_path}"
    raise FileNotFoundError(msg)


def load_modular_config(config_dir: Path) -> NetworkConfig:
    """Load configuration from modular config directory structure."""
    try:
        # Load main config
        config_file = config_dir / "config.yml"
        devices_file = config_dir / "devices.yml"
        devices_dir = config_dir / "devices"
        groups_file = config_dir / "groups.yml"
        sequences_file = config_dir / "sequences.yml"

        # Ensure required files exist
        if not config_file.exists():
            msg = f"Main config file not found: {config_file}"
            raise FileNotFoundError(msg)
        if not devices_file.exists():
            msg = f"Devices config file not found: {devices_file}"
            raise FileNotFoundError(msg)

        # Load main config
        with config_file.open("r", encoding="utf-8") as f:
            main_config: dict[str, Any] = yaml.safe_load(f) or {}

        # Load devices from base file
        with devices_file.open("r", encoding="utf-8") as f:
            devices_config: dict[str, Any] = yaml.safe_load(f) or {}

        # Optionally extend/override devices from a devices/ directory for per-customer splits
        if devices_dir.exists() and devices_dir.is_dir():
            merged_devices: dict[str, Any] = dict(devices_config.get("devices", {}))

            # Load optional defaults from _defaults.yml to be applied (shallow) to each device loaded from dir
            dir_defaults: dict[str, Any] = {}
            defaults_file = devices_dir / "_defaults.yml"
            if defaults_file.exists():
                try:
                    with defaults_file.open("r", encoding="utf-8") as f:
                        defaults_raw: dict[str, Any] | Any = yaml.safe_load(f) or {}
                    if isinstance(defaults_raw, dict):
                        dir_defaults = defaults_raw.get("defaults", {}) or {}
                except yaml.YAMLError as e:
                    logging.warning(
                        f"Invalid YAML in devices defaults file {defaults_file}: {e}"
                    )

            files = sorted(devices_dir.glob("*.yml")) + sorted(
                devices_dir.glob("*.yaml")
            )
            for file in files:
                if file.name.startswith("_"):
                    # Skip special files like _defaults.yml
                    continue
                try:
                    with file.open("r", encoding="utf-8") as f:
                        fragment: dict[str, Any] = yaml.safe_load(f) or {}
                except yaml.YAMLError as e:
                    logging.warning(f"Invalid YAML in devices file {file}: {e}")
                    continue

                fragment_devices_raw = fragment.get("devices", {})
                if not isinstance(fragment_devices_raw, dict):
                    logging.warning(
                        "Unexpected structure in %s; expected 'devices' mapping. "
                        "Skipping.",
                        file,
                    )
                    continue

                # Apply shallow defaults and merge. Directory devices override base when
                # keys collide.
                for dev_name, dev_cfg in fragment_devices_raw.items():
                    if isinstance(dev_cfg, dict) and dir_defaults:
                        merged_devices[dev_name] = {**dir_defaults, **dev_cfg}
                    else:
                        merged_devices[dev_name] = dev_cfg

            # Replace devices in config with merged result
            devices_config["devices"] = merged_devices

        # Load groups (optional)
        groups_config: dict[str, Any] = {}
        if groups_file.exists():
            with groups_file.open("r", encoding="utf-8") as f:
                groups_config = yaml.safe_load(f) or {}

        # Load sequences (optional)
        sequences_config: dict[str, Any] = {}
        if sequences_file.exists():
            with sequences_file.open("r", encoding="utf-8") as f:
                sequences_config = yaml.safe_load(f) or {}

        # Load vendor-specific sequences
        vendor_sequences = _load_vendor_sequences(config_dir, sequences_config)

        # Merge all configs into the expected format
        merged_config: dict[str, Any] = {
            "general": main_config.get("general", {}),
            "devices": devices_config.get("devices", {}),
            "device_groups": groups_config.get("groups", {}),
            "global_command_sequences": sequences_config.get("sequences", {}),
            "vendor_platforms": sequences_config.get("vendor_platforms", {}),
            "vendor_sequences": vendor_sequences,
        }

        logging.debug(f"Loaded modular configuration from {config_dir}")
        return NetworkConfig(**merged_config)

    except yaml.YAMLError as e:
        msg = f"Invalid YAML in modular configuration: {config_dir}"
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Failed to load modular configuration from {config_dir}: {e}"
        raise ValueError(msg) from e


def _load_vendor_sequences(
    config_dir: Path, sequences_config: dict[str, Any]
) -> dict[str, dict[str, VendorSequence]]:
    """Load vendor-specific sequences from sequences directory."""
    vendor_sequences: dict[str, dict[str, VendorSequence]] = {}

    # Get vendor platform configurations
    vendor_platforms = sequences_config.get("vendor_platforms", {})

    for platform_name, platform_config in vendor_platforms.items():
        platform_sequences: dict[str, VendorSequence] = {}

        # Build path to vendor sequences
        sequence_path = config_dir / platform_config.get("sequence_path", "")

        if not sequence_path.exists():
            logging.debug(f"Vendor sequence path not found: {sequence_path}")
            continue

        # Load default sequence files for this vendor
        default_files = platform_config.get("default_files", ["common.yml"])

        for sequence_file in default_files:
            vendor_file_path = sequence_path / sequence_file

            if not vendor_file_path.exists():
                logging.debug(f"Vendor sequence file not found: {vendor_file_path}")
                continue

            try:
                with vendor_file_path.open("r", encoding="utf-8") as f:
                    vendor_config: dict[str, Any] = yaml.safe_load(f) or {}

                # Load sequences from the vendor file
                sequences = vendor_config.get("sequences", {})
                for seq_name, seq_data in sequences.items():
                    platform_sequences[seq_name] = VendorSequence(**seq_data)

                logging.debug(
                    f"Loaded {len(sequences)} sequences for {platform_name} "
                    f"from {vendor_file_path}"
                )

            except yaml.YAMLError as e:
                logging.warning(
                    f"Invalid YAML in vendor sequence file {vendor_file_path}: {e}"
                )
                continue
            except Exception as e:
                logging.warning(
                    f"Failed to load vendor sequence file {vendor_file_path}: {e}"
                )
                continue

        if platform_sequences:
            vendor_sequences[platform_name] = platform_sequences

    return vendor_sequences


def load_legacy_config(config_path: Path) -> NetworkConfig:
    """Load configuration from legacy monolithic YAML file."""
    try:
        with config_path.open("r", encoding="utf-8") as f:
            raw_config: dict[str, Any] = yaml.safe_load(f) or {}

        # Log config loading for debugging
        logging.debug(f"Loaded legacy configuration from {config_path}")

        return NetworkConfig(**raw_config)

    except yaml.YAMLError as e:
        msg = f"Invalid YAML in configuration file: {config_path}"
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Failed to load configuration from {config_path}: {e}"
        raise ValueError(msg) from e
