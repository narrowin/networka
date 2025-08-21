# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Configuration management for network toolkit."""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from network_toolkit.common.paths import default_modular_config_dir
from network_toolkit.credentials import (
    ConnectionParameterBuilder,
    EnvironmentCredentialManager,
)
from network_toolkit.exceptions import NetworkToolkitError


def load_dotenv_files(config_path: Path | None = None) -> None:
    """
    Load environment variables from .env files.

    Precedence order (highest to lowest):
    1. Environment variables already set (highest priority)
    2. .env in config directory (if config_path provided)
    3. .env in current working directory (lowest priority)

    Parameters
    ----------
    config_path : Path | None
        Path to the configuration file (used to locate adjacent .env file)
    """
    # Store any existing NW_* environment variables to preserve their precedence
    # These are the "real" environment variables that should have highest priority
    original_nw_vars = {k: v for k, v in os.environ.items() if k.startswith("NW_")}

    # Load .env from current working directory first (lowest priority)
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        logging.debug(f"Loading .env from current directory: {cwd_env}")
        load_dotenv(cwd_env, override=False)

    # Load .env from config directory (if config_path provided)
    if config_path:
        config_dir = config_path.parent if config_path.is_file() else config_path
        config_env = config_dir / ".env"
        if config_env.exists():
            logging.debug(f"Loading .env from config directory: {config_env}")
            # This will override any values loaded from cwd .env
            load_dotenv(config_env, override=True)

    # Finally, restore any environment variables that existed BEFORE we started loading .env files
    # This ensures that environment variables set by the user have the highest precedence
    for key, value in original_nw_vars.items():
        os.environ[key] = value


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

    # Output formatting configuration
    output_mode: str = "default"

    @property
    def default_user(self) -> str:
        """Get default username from environment variable."""
        user = EnvironmentCredentialManager.get_default("user")
        if not user:
            msg = "Default username not found in environment. Please set NW_USER_DEFAULT environment variable."
            raise ValueError(msg)
        return user

    @property
    def default_password(self) -> str:
        """Get default password from environment variable."""
        password = EnvironmentCredentialManager.get_default("password")
        if not password:
            msg = "Default password not found in environment. Please set NW_PASSWORD_DEFAULT environment variable."
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

    @field_validator("output_mode")
    @classmethod
    def validate_output_mode(cls, v: str) -> str:
        """Validate output mode is supported."""
        if v.lower() not in ["default", "light", "dark", "no-color", "raw"]:
            msg = "output_mode must be one of: default, light, dark, no-color, raw"
            raise ValueError(msg)
        return v.lower()


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


class GroupCredentials(BaseModel):
    """Group-level credential configuration."""

    user: str | None = None
    password: str | None = None


class DeviceGroup(BaseModel):
    """Configuration for a device group."""

    description: str
    members: list[str] | None = None
    match_tags: list[str] | None = None
    credentials: GroupCredentials | None = None


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
        Get connection parameters for a device using the builder pattern.

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
        builder = ConnectionParameterBuilder(self)
        return builder.build_parameters(
            device_name, username_override, password_override
        )

    def get_group_members(self, group_name: str) -> list[str]:
        """Get list of device names in a group."""
        if not self.device_groups or group_name not in self.device_groups:
            msg = f"Device group '{group_name}' not found in configuration"
            raise NetworkToolkitError(msg, details={"group": group_name})

        group = self.device_groups[group_name]
        members: list[str] = []

        # Direct members
        if group.members:
            members.extend(
                [m for m in group.members if self.devices and m in self.devices]
            )

        # Tag-based members
        if group.match_tags and self.devices:
            for device_name, device in self.devices.items():
                if device.tags and all(tag in device.tags for tag in group.match_tags):
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

        matching_sequences: dict[str, CommandSequence] = {}
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

    def get_device_groups(self, device_name: str) -> list[str]:
        """
        Get all groups that a device belongs to.

        Parameters
        ----------
        device_name : str
            Name of the device

        Returns
        -------
        list[str]
            List of group names the device belongs to
        """
        device_groups: list[str] = []
        if not self.device_groups or not self.devices:
            return device_groups

        device = self.devices.get(device_name) if self.devices else None
        if not device:
            return device_groups

        for group_name, group_config in (self.device_groups or {}).items():
            # Check explicit membership
            if group_config.members and device_name in group_config.members:
                device_groups.append(group_name)
                continue

            # Check tag-based membership
            if (
                group_config.match_tags
                and device.tags
                and any(tag in device.tags for tag in group_config.match_tags)
            ):
                device_groups.append(group_name)

        return device_groups

    def get_group_credentials(self, device_name: str) -> tuple[str | None, str | None]:
        """
        Get group-level credentials for a device using the environment manager.

        Checks all groups the device belongs to and returns the first
        group credentials found, prioritizing by group order.

        Parameters
        ----------
        device_name : str
            Name of the device

        Returns
        -------
        tuple[str | None, str | None]
            Tuple of (username, password) from group credentials, or (None, None)
        """
        device_groups = self.get_device_groups(device_name)

        for group_name in device_groups:
            group = self.device_groups.get(group_name) if self.device_groups else None
            if group and group.credentials:
                # Check for explicit credentials in group config
                if group.credentials.user or group.credentials.password:
                    return (group.credentials.user, group.credentials.password)

                # Check for environment variables for this group
                group_user = EnvironmentCredentialManager.get_group_specific(
                    group_name, "user"
                )
                group_password = EnvironmentCredentialManager.get_group_specific(
                    group_name, "password"
                )
                if group_user or group_password:
                    return (group_user, group_password)

        return (None, None)


# CSV/Discovery/Merge helpers


def _load_csv_devices(csv_path: Path) -> dict[str, DeviceConfig]:
    """
    Load device configurations from CSV file.

    Expected CSV headers: name,host,device_type,description,platform,model,location,tags
    Tags should be semicolon-separated in a single column.
    """
    devices: dict[str, DeviceConfig] = {}

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue

                # Parse tags from semicolon-separated string
                tags_str = row.get("tags", "").strip()
                tags = (
                    [tag.strip() for tag in tags_str.split(";") if tag.strip()]
                    if tags_str
                    else None
                )

                device_config = DeviceConfig(
                    host=row.get("host", "").strip(),
                    device_type=row.get("device_type", "mikrotik_routeros").strip(),
                    description=row.get("description", "").strip() or None,
                    platform=row.get("platform", "").strip() or None,
                    model=row.get("model", "").strip() or None,
                    location=row.get("location", "").strip() or None,
                    tags=tags,
                )

                devices[name] = device_config

        logging.debug(f"Loaded {len(devices)} devices from CSV: {csv_path}")
        return devices

    except Exception as e:  # pragma: no cover - robustness
        logging.warning(f"Failed to load devices from CSV {csv_path}: {e}")
        return {}


def _load_csv_groups(csv_path: Path) -> dict[str, DeviceGroup]:
    """
    Load device group configurations from CSV file.

    Expected CSV headers: name,description,members,match_tags
    Members and match_tags should be semicolon-separated.
    """
    groups: dict[str, DeviceGroup] = {}

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue

                # Parse members from semicolon-separated string
                members_str = row.get("members", "").strip()
                members = (
                    [m.strip() for m in members_str.split(";") if m.strip()]
                    if members_str
                    else None
                )

                # Parse match_tags from semicolon-separated string
                tags_str = row.get("match_tags", "").strip()
                match_tags = (
                    [tag.strip() for tag in tags_str.split(";") if tag.strip()]
                    if tags_str
                    else None
                )

                group_config = DeviceGroup(
                    description=row.get("description", "").strip(),
                    members=members,
                    match_tags=match_tags,
                )

                groups[name] = group_config

        logging.debug(f"Loaded {len(groups)} groups from CSV: {csv_path}")
        return groups

    except Exception as e:  # pragma: no cover - robustness
        logging.warning(f"Failed to load groups from CSV {csv_path}: {e}")
        return {}


def _load_csv_sequences(csv_path: Path) -> dict[str, CommandSequence]:
    """
    Load command sequence configurations from CSV file.

    Expected CSV headers: name,description,commands,tags
    Commands and tags should be semicolon-separated.
    """
    sequences: dict[str, CommandSequence] = {}

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue

                # Parse commands from semicolon-separated string
                commands_str = row.get("commands", "").strip()
                commands = [
                    cmd.strip() for cmd in commands_str.split(";") if cmd.strip()
                ]

                if not commands:
                    logging.warning(f"Sequence '{name}' has no commands, skipping")
                    continue

                # Parse tags from semicolon-separated string
                tags_str = row.get("tags", "").strip()
                tags = (
                    [tag.strip() for tag in tags_str.split(";") if tag.strip()]
                    if tags_str
                    else None
                )

                sequence_config = CommandSequence(
                    description=row.get("description", "").strip(),
                    commands=commands,
                    tags=tags,
                )

                sequences[name] = sequence_config

        logging.debug(f"Loaded {len(sequences)} sequences from CSV: {csv_path}")
        return sequences

    except Exception as e:  # pragma: no cover - robustness
        logging.warning(f"Failed to load sequences from CSV {csv_path}: {e}")
        return {}


def _discover_config_files(config_dir: Path, config_type: str) -> list[Path]:
    """
    Discover configuration files of a specific type in config directory and subdirectories.

    Looks for both YAML and CSV files in:
    - config_dir/{config_type}.yml
    - config_dir/{config_type}.csv
    - config_dir/{config_type}/{config_type}.yml
    - config_dir/{config_type}/{config_type}.csv
    - config_dir/{config_type}/*.yml
    - config_dir/{config_type}/*.csv
    """
    files: list[Path] = []

    # Main config file in root
    for ext in [".yml", ".yaml", ".csv"]:
        main_file = config_dir / f"{config_type}{ext}"
        if main_file.exists():
            files.append(main_file)

    # Subdirectory files
    subdir = config_dir / config_type
    if subdir.exists() and subdir.is_dir():
        # Main file in subdirectory
        for ext in [".yml", ".yaml", ".csv"]:
            sub_main_file = subdir / f"{config_type}{ext}"
            if sub_main_file.exists():
                files.append(sub_main_file)

        # All yaml/csv files in subdirectory
        for pattern in ["*.yml", "*.yaml", "*.csv"]:
            files.extend(subdir.glob(pattern))

    # Remove duplicates while preserving order
    seen: set[Path] = set()
    unique_files: list[Path] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    return unique_files


def _merge_configs(
    base_config: dict[str, Any], override_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge two configuration dictionaries with override precedence.

    More specific configs (from subdirectories or later files) override general ones.
    """
    merged = base_config.copy()

    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            merged[key] = _merge_configs(merged[key], value)
        else:
            # Override with new value
            merged[key] = value

    return merged


def load_config(config_path: str | Path) -> NetworkConfig:
    """
    Load and validate configuration from YAML file(s).

    Supports both:
    1. New modular config: config_path as directory containing config/, devices.yml,
       groups.yml, sequences.yml
    2. Legacy monolithic: config_path as single devices.yml file

    Additionally loads environment variables from .env files before loading config.
    """
    config_path = Path(config_path)
    original_path = config_path  # Keep track of original user input

    # Load .env files first to make environment variables available for credential resolution
    load_dotenv_files(config_path)

    # Check for new modular configuration structure
    # Handle default path "config" - check current directory first, then fall back to platform default
    if config_path.name in ["config", "config/"]:
        # First try current directory
        if config_path.exists():
            return load_modular_config(config_path)
        # Fall through to platform default logic below

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
        # Prefer platform default location first
        platform_default = default_modular_config_dir()
        possible_paths: list[Path] = []
        if (platform_default / "config.yml").exists():
            possible_paths.append(platform_default / "config.yml")
        possible_paths.extend(
            [
                Path("config/config.yml"),  # Modular config in CWD
                Path("devices.yml"),  # Legacy config in root
            ]
        )

        for path in possible_paths:
            if path.exists():
                if path.name == "config.yml":
                    # Check if this is a modular config by looking for devices/ or groups/ directories
                    parent_dir = path.parent
                    if (parent_dir / "devices").exists() or (
                        parent_dir / "groups"
                    ).exists():
                        return load_modular_config(parent_dir)
                    # Fall back to legacy loading
                    return load_legacy_config(path)
                else:
                    return load_legacy_config(path)

    # Final attempt: platform default modular path
    platform_default_dir = default_modular_config_dir()
    if (platform_default_dir / "config.yml").exists():
        return load_modular_config(platform_default_dir)

    # If we get here, nothing was found
    msg = f"Configuration file not found: {config_path}"
    raise FileNotFoundError(msg)


def load_modular_config(config_dir: Path) -> NetworkConfig:
    """Load configuration from modular config directory structure with enhanced discovery."""
    try:
        # Load main config
        config_file = config_dir / "config.yml"
        if not config_file.exists():
            msg = f"Main config file not found: {config_file}"
            raise FileNotFoundError(msg)

        with config_file.open("r", encoding="utf-8") as f:
            main_config: dict[str, Any] = yaml.safe_load(f) or {}

        # Enhanced device loading with CSV support and subdirectory discovery
        all_devices: dict[str, Any] = {}
        device_defaults: dict[str, Any] = {}
        device_files = _discover_config_files(config_dir, "devices")

        # Load defaults first
        devices_dir = config_dir / "devices"
        if devices_dir.exists():
            defaults_file = devices_dir / "_defaults.yml"
            if defaults_file.exists():
                try:
                    with defaults_file.open("r", encoding="utf-8") as f:
                        defaults_config: dict[str, Any] = yaml.safe_load(f) or {}
                        device_defaults = defaults_config.get("defaults", {})
                except yaml.YAMLError as e:
                    logging.warning(
                        f"Invalid YAML in defaults file {defaults_file}: {e}"
                    )

        # Load device files
        for device_file in device_files:
            # Skip defaults file as it's handled separately
            if device_file.name == "_defaults.yml":
                continue

            if device_file.suffix.lower() == ".csv":
                file_devices = _load_csv_devices(device_file)
                # Apply defaults to CSV devices
                for _device_name, device_config in file_devices.items():
                    for key, default_value in device_defaults.items():
                        if getattr(device_config, key, None) is None:
                            setattr(device_config, key, default_value)
                all_devices.update(file_devices)
            else:
                try:
                    with device_file.open("r", encoding="utf-8") as f:
                        device_yaml_config: dict[str, Any] = yaml.safe_load(f) or {}
                        file_devices = device_yaml_config.get("devices", {})
                        if isinstance(file_devices, dict):
                            # Apply defaults to YAML devices
                            for _device_name, device_config in file_devices.items():
                                for key, default_value in device_defaults.items():
                                    if key not in device_config:
                                        device_config[key] = default_value
                            all_devices.update(file_devices)
                        else:
                            logging.warning(
                                f"Invalid devices structure in {device_file}, skipping"
                            )
                except yaml.YAMLError as e:
                    logging.warning(f"Invalid YAML in {device_file}: {e}")

        # Enhanced group loading with CSV support and subdirectory discovery
        all_groups: dict[str, Any] = {}
        group_files = _discover_config_files(config_dir, "groups")

        for group_file in group_files:
            if group_file.suffix.lower() == ".csv":
                file_groups = _load_csv_groups(group_file)
                all_groups.update(file_groups)
            else:
                try:
                    with group_file.open("r", encoding="utf-8") as f:
                        group_yaml_config: dict[str, Any] = yaml.safe_load(f) or {}
                        file_groups = group_yaml_config.get("groups", {})
                        if isinstance(file_groups, dict):
                            all_groups.update(file_groups)
                        else:
                            logging.warning(
                                f"Invalid groups structure in {group_file}, skipping"
                            )
                except yaml.YAMLError as e:
                    logging.warning(f"Invalid YAML in {group_file}: {e}")

        # Enhanced sequence loading with CSV support and subdirectory discovery
        all_sequences: dict[str, Any] = {}
        sequence_files = _discover_config_files(config_dir, "sequences")
        sequences_config: dict[str, Any] = {}

        for seq_file in sequence_files:
            if seq_file.suffix.lower() == ".csv":
                file_sequences = _load_csv_sequences(seq_file)
                all_sequences.update(file_sequences)
            else:
                try:
                    with seq_file.open("r", encoding="utf-8") as f:
                        seq_yaml_config: dict[str, Any] = yaml.safe_load(f) or {}
                        # Extract sequences
                        file_sequences = seq_yaml_config.get("sequences", {})
                        if isinstance(file_sequences, dict):
                            all_sequences.update(file_sequences)

                        # Keep track of other sequence config for vendor sequences
                        if not sequences_config:
                            sequences_config = seq_yaml_config
                        else:
                            sequences_config = _merge_configs(
                                sequences_config, seq_yaml_config
                            )
                except yaml.YAMLError as e:
                    logging.warning(f"Invalid YAML in {seq_file}: {e}")

        # Load vendor-specific sequences
        vendor_sequences = _load_vendor_sequences(config_dir, sequences_config)

        # Merge all configs into the expected format
        merged_config: dict[str, Any] = {
            "general": main_config.get("general", {}),
            "devices": all_devices,
            "device_groups": all_groups,
            "global_command_sequences": all_sequences,
            "vendor_platforms": sequences_config.get("vendor_platforms", {}),
            "vendor_sequences": vendor_sequences,
        }

        logging.debug(f"Loaded modular configuration from {config_dir}")
        logging.debug(f"  - Devices: {len(all_devices)}")
        logging.debug(f"  - Groups: {len(all_groups)}")
        logging.debug(f"  - Sequences: {len(all_sequences)}")

        return NetworkConfig(**merged_config)

    except yaml.YAMLError as e:
        msg = f"Invalid YAML in modular configuration: {config_dir}"
        raise ValueError(msg) from e
    except FileNotFoundError:
        # Re-raise FileNotFoundError as-is for missing config files
        raise
    except Exception as e:  # pragma: no cover - safety
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
                    f"Loaded {len(sequences)} sequences for {platform_name} from {vendor_file_path}"
                )

            except yaml.YAMLError as e:
                logging.warning(
                    f"Invalid YAML in vendor sequence file {vendor_file_path}: {e}"
                )
                continue
            except Exception as e:  # pragma: no cover - robustness
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
    except Exception as e:  # pragma: no cover - safety
        msg = f"Failed to load configuration from {config_path}: {e}"
        raise ValueError(msg) from e
