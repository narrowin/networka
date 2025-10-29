# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Configuration management for network toolkit."""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
from typing import Any, cast

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, PrivateAttr, field_validator

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH

# from network_toolkit.common.paths import default_modular_config_dir
from network_toolkit.credentials import (
    ConnectionParameterBuilder,
    EnvironmentCredentialManager,
)
from network_toolkit.exceptions import NetworkToolkitError


def _resolve_fallback_config_path(original_hint: Path | None = None) -> Path | None:
    """Best-effort fallback discovery for a modular config directory.

    Order:
    1) NW_CONFIG_DIR environment variable, if it exists
    2) Search upwards from current working directory for a folder named 'config'
    3) If an original hint is provided, search upwards from that location as well

    Returns a Path to a directory if found, otherwise None.
    """
    # 1) Explicit environment override
    env_dir = os.environ.get("NW_CONFIG_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists() and p.is_dir():
            return p

    def search_up(start: Path) -> Path | None:
        cur = start
        seen = 0
        while True:
            candidate = cur / "config"
            if candidate.exists() and candidate.is_dir():
                return candidate
            if cur.parent == cur or seen > 12:  # avoid deep walks
                return None
            cur = cur.parent
            seen += 1

    # 2) From CWD
    cwd_found = search_up(Path.cwd())
    if cwd_found is not None:
        return cwd_found

    # 3) From original hint
    if original_hint is not None:
        try:
            hint_found = search_up(original_hint.resolve())
        except Exception:
            hint_found = None
        if hint_found is not None:
            return hint_found

    return None


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
        logging.debug(f"Loading .env from current directory: {cwd_env.resolve()}")
        load_dotenv(cwd_env, override=False)

    # Load .env from config directory (if config_path provided)
    if config_path:
        config_dir = config_path.parent if config_path.is_file() else config_path
        config_env = config_dir / ".env"
        if config_env.exists():
            logging.debug(f"Loading .env from config directory: {config_env.resolve()}")
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
    transport: str = "system"
    port: int = 22
    timeout: int = 30
    default_transport_type: str = "scrapli"
    ssh_config_file: bool = True
    ssh_strict_host_key_checking: bool = (
        False  # accept-new: auto-accept new keys, verify existing
    )

    # Connection retry settings
    connection_retries: int = 3
    retry_delay: int = 5

    # File transfer settings
    transfer_timeout: int = 300
    verify_checksums: bool = True

    # Command execution settings
    command_timeout: int = 60
    enable_logging: bool = True
    log_level: str = "WARNING"

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
        valid_transports = [
            "system",
            "paramiko",
            "ssh2",
            "telnet",
            "asyncssh",
            "asynctelnet",
        ]
        if v.lower() not in valid_transports:
            msg = f"transport must be one of: {', '.join(valid_transports)}"
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

    @field_validator("ssh_strict_host_key_checking")
    @classmethod
    def validate_ssh_strict_host_key_checking(cls, v: Any) -> bool:
        """Validate SSH strict host key checking setting."""
        if not isinstance(v, bool):
            msg = "ssh_strict_host_key_checking must be a boolean"
            raise ValueError(msg)
        return v


class DeviceOverrides(BaseModel):
    """Device-specific configuration overrides."""

    user: str | None = None
    password: str | None = None
    port: int | None = None
    timeout: int | None = None
    transport: str | None = None
    command_timeout: int | None = None
    transfer_timeout: int | None = None


# Device type is intentionally a free-form string at config load time.
# Validation of supported values occurs at runtime where appropriate.
SupportedDeviceType = str


class DeviceConfig(BaseModel):
    """Configuration for a single network device.

    Attributes
    ----------
    device_type : SupportedDeviceType
        Network driver type for connection establishment and command execution.
        Determines which Scrapli/Netmiko platform driver to use for network operations.
        Examples: 'mikrotik_routeros', 'cisco_iosxe', 'juniper_junos'

    platform : str | None
        Hardware architecture platform for firmware operations.
        Used to select correct firmware images for upgrades and hardware-specific operations.
        Examples: 'x86', 'x86_64', 'arm', 'tile', 'mipsbe'
        Optional - only required for firmware upgrade operations.
    """

    host: str
    description: str | None = None
    device_type: SupportedDeviceType = (
        "mikrotik_routeros"  # Default to most common type
    )
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

    # Private: where this device was loaded from
    _source_path: Path | None = PrivateAttr(default=None)

    def set_source_path(self, path: Path) -> None:
        """Set the source path where this device was defined."""
        self._source_path = path


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

    # Private: where this group was loaded from
    _source_path: Path | None = PrivateAttr(default=None)

    def set_source_path(self, path: Path) -> None:
        """Set the source path where this group was defined."""
        self._source_path = path


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

    # Private: where this vendor sequence was loaded from
    _source_path: Path | None = PrivateAttr(default=None)

    def set_source_path(self, path: Path) -> None:
        """Set the source path where this vendor sequence was defined."""
        self._source_path = path


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
    command_sequence_groups: dict[str, CommandSequenceGroup] | None = None
    file_operations: dict[str, FileOperationConfig] | None = None

    # Multi-vendor support
    vendor_platforms: dict[str, VendorPlatformConfig] | None = None
    vendor_sequences: dict[str, dict[str, VendorSequence]] | None = None
    global_command_sequences: dict[str, VendorSequence] | None = None

    # Helper: device source path accessor (non-schema, uses PrivateAttr on DeviceConfig)
    def get_device_source_path(self, device_name: str) -> Path | None:
        dev = self.devices.get(device_name) if self.devices else None
        if dev is None:
            return None
        return getattr(dev, "_source_path", None)

    # Helper: group source path accessor (non-schema, uses PrivateAttr on DeviceGroup)
    def get_group_source_path(self, group_name: str) -> Path | None:
        grp = self.device_groups.get(group_name) if self.device_groups else None
        if grp is None:
            return None
        return getattr(grp, "_source_path", None)

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

    def get_transport_type(
        self, device_name: str, transport_override: str | None = None
    ) -> str:
        """
        Get the transport type for a device.

        Parameters
        ----------
        device_name : str
            Name of the device
        transport_override : str | None
            Override transport type from CLI or other source

        Returns
        -------
        str
            Transport type (currently only 'scrapli' is supported)
        """
        # CLI override takes highest precedence
        if transport_override:
            return transport_override

        if not self.devices or device_name not in self.devices:
            return self.general.default_transport_type

        device = self.devices[device_name]
        return device.transport_type or self.general.default_transport_type

    def list_command_sequence_groups(self) -> dict[str, CommandSequenceGroup]:
        """
        List all available command sequence groups.

        Returns
        -------
        dict[str, CommandSequenceGroup]
            Dictionary of group names to CommandSequenceGroup objects
        """
        return self.command_sequence_groups or {}

    def resolve_sequence_commands(
        self, sequence_name: str, device_name: str
    ) -> list[str] | None:
        """
        Resolve sequence commands for a specific device.

        This method delegates to SequenceManager for actual resolution logic,
        which considers device-specific, vendor-specific, and global sequences.

        Parameters
        ----------
        sequence_name : str
            Name of the sequence to resolve
        device_name : str
            Name of the device for vendor-specific resolution

        Returns
        -------
        list[str] | None
            List of commands if sequence found, None otherwise
        """
        from network_toolkit.sequence_manager import SequenceManager

        sm = SequenceManager(self)
        return sm.resolve(sequence_name, device_name)

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

                # Validate device_type and use fallback if invalid
                device_type_raw = row.get("device_type", "linux").strip()
                valid_types = {
                    "mikrotik_routeros",
                    "cisco_iosxe",
                    "cisco_ios",
                    "cisco_iosxr",
                    "cisco_nxos",
                    "juniper_junos",
                    "arista_eos",
                    "linux",
                    "generic",
                }
                device_type = cast(
                    SupportedDeviceType,
                    device_type_raw if device_type_raw in valid_types else "linux",
                )

                device_config = DeviceConfig(
                    host=row.get("host", "").strip(),
                    device_type=device_type,  # Now guaranteed to be valid
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


def _load_csv_sequences(csv_path: Path) -> dict[str, VendorSequence]:
    """
    Load command sequence configurations from CSV file.

    Expected CSV headers: name,description,commands,category,device_types
    Commands and device_types should be semicolon-separated.
    """
    sequences: dict[str, VendorSequence] = {}

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue

                # Parse commands from semicolon-separated string
                commands_str = row.get("commands", "").strip()
                if not commands_str:
                    continue  # Skip sequences without commands

                commands = [
                    cmd.strip() for cmd in commands_str.split(";") if cmd.strip()
                ]

                # Parse device_types from semicolon-separated string
                device_types_str = row.get("device_types", "").strip()
                device_types = (
                    [dt.strip() for dt in device_types_str.split(";") if dt.strip()]
                    if device_types_str
                    else None
                )

                sequence_config = VendorSequence(
                    description=row.get("description", "").strip(),
                    commands=commands,
                    category=row.get("category", "").strip() or None,
                    device_types=device_types,
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
    Load and validate configuration.

    Supported mode:
    - Modular directory: a directory containing config.yml and optional
      devices/, groups/, sequences/ subdirs and/or companion YAML/CSV files.
      If a directory is supplied, it must contain config.yml. Missing
      config.yml raises FileNotFoundError("Main config file not found").

    Additionally, passing a direct path to a config.yml file is supported and
    will be treated as the parent directory in modular mode.

    Legacy single-file YAML mode is not supported.

    When no --config is provided elsewhere, callers should pass DEFAULT_CONFIG_PATH.
    If the default user config directory does not exist, we will fall back to
    discovering a local 'config' directory relative to the current working
    directory (or its ancestors), or NW_CONFIG_DIR if set.
    """

    # Normalize input
    config_path = Path(config_path)

    # If caller passed the default sentinel path, honor NW_CONFIG_DIR explicitly
    # so tests and callers can force a specific config/ directory regardless of
    # whether a user-level DEFAULT_CONFIG_PATH exists.
    if config_path == DEFAULT_CONFIG_PATH:
        env_dir = os.environ.get("NW_CONFIG_DIR")
        if env_dir:
            env_path = Path(env_dir)
            if env_path.exists() and env_path.is_dir():
                # Load .env using the discovered directory and proceed as modular config
                load_dotenv_files(env_path)
                config = load_modular_config(env_path)
                _auto_export_schemas_if_project()
                return config

        # For DEFAULT_CONFIG_PATH, only use the explicit default path
        # Do NOT search for local config/ directories
        # This ensures consistent behavior across different working directories

    # Load .env files to make environment variables available for credential resolution
    # using the original hint path. This happens after the NW_CONFIG_DIR fast path above.
    load_dotenv_files(config_path)

    # When path doesn't exist, provide file vs dir specific messaging
    if not config_path.exists():
        # Explicit file path provided
        if config_path.suffix.lower() in {".yml", ".yaml"}:
            msg = f"Configuration file not found: {config_path}"
            raise FileNotFoundError(msg)
        # Default path missing — surface clearly but without probing CWD
        if config_path == DEFAULT_CONFIG_PATH:
            # For DEFAULT_CONFIG_PATH, do not attempt fallback discovery
            # This ensures consistent behavior regardless of working directory
            msg = f"Configuration directory not found: {config_path}"
            raise FileNotFoundError(msg)
        msg = f"Configuration path not found: {config_path}"
        raise FileNotFoundError(msg)

    # Direct file path: treat any *.yml/*.yaml as the main modular config file
    if config_path.is_file():
        if config_path.suffix.lower() in {".yml", ".yaml"}:
            config_dir = config_path.parent
            config = load_modular_config(config_dir, main_config_path=config_path)
            _auto_export_schemas_if_project()
            return config
        msg = "Unsupported configuration file; expected a YAML file (*.yml/*.yaml)."
        raise FileNotFoundError(msg)

    # Modular directory mode — must contain config.yml
    direct_config_file = config_path / "config.yml"
    if not direct_config_file.exists():
        msg = f"Main config file not found: {direct_config_file}"
        raise FileNotFoundError(msg)

    config = load_modular_config(config_path)
    _auto_export_schemas_if_project()
    return config


def _auto_export_schemas_if_project() -> None:
    """
    Automatically export schemas if we're in a project directory.

    Only exports if:
    1. We're working with a local config (not global system config)
    2. Schemas don't already exist or are outdated
    3. Working directory appears to be a project (has .git, pyproject.toml, etc.)
    """
    import time
    from pathlib import Path

    # Check if this looks like a project directory
    project_indicators = [
        Path(".git"),
        Path("pyproject.toml"),
        Path("package.json"),
        Path("Cargo.toml"),
        Path("go.mod"),
    ]

    if not any(indicator.exists() for indicator in project_indicators):
        logging.debug("Not in a project directory, skipping schema export")
        return

    schema_dir = Path("schemas")
    schema_file = schema_dir / "network-config.schema.json"

    # Check if schemas need updating (don't export every time)
    if schema_file.exists():
        # Check if schema is less than 1 day old
        schema_age = time.time() - schema_file.stat().st_mtime
        if schema_age < 86400:  # 24 hours
            logging.debug("Schemas are up to date, skipping export")
            return

    try:
        export_schemas_to_workspace()
        logging.debug("Auto-exported JSON schemas for editor validation")
    except Exception as e:
        # Don't fail config loading if schema export fails
        logging.debug(f"Failed to auto-export schemas: {e}")


def _is_project_config(config_path: Path) -> bool:
    """Check if this is a project-local config vs global system config."""
    try:
        # If config is in current directory tree, consider it project config
        cwd = Path.cwd()
        config_path.resolve().relative_to(cwd.resolve())
        return True
    except ValueError:
        # Config is outside current directory tree (likely global)
        return False


def load_modular_config(
    config_dir: Path, *, main_config_path: Path | None = None
) -> NetworkConfig:
    """Load configuration from modular config directory structure with enhanced discovery.

    Parameters
    ----------
    config_dir : Path
        The directory that contains the modular configuration files.
    main_config_path : Path | None
        Optional explicit path to the main config YAML file. When provided,
        this file will be used instead of "config.yml". This enables callers
        to pass a direct YAML file path and still leverage modular discovery
        for devices/, groups/, and sequences/ under the parent directory.
    """
    try:
        # Load main config (either explicit file or default config.yml)
        config_file = main_config_path or (config_dir / "config.yml")
        if not config_file.exists():
            msg = f"Main config file not found: {config_file}"
            raise FileNotFoundError(msg)

        try:
            with config_file.open("r", encoding="utf-8") as f:
                main_config: dict[str, Any] = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:  # surface clear error for top-level file
            msg = "Invalid YAML in configuration file"
            raise ValueError(msg) from e

        # Enhanced device loading with CSV support and subdirectory discovery
        all_devices: dict[str, Any] = {}
        device_defaults: dict[str, Any] = {}
        device_files = _discover_config_files(config_dir, "devices")
        device_sources: dict[str, Path] = {}

        # Load defaults first
        devices_dir = config_dir / "devices"
        if devices_dir.exists():
            defaults_file = devices_dir / "_defaults.yml"
            if defaults_file.exists():
                try:
                    with defaults_file.open("r", encoding="utf-8") as df:
                        defaults_config: dict[str, Any] = yaml.safe_load(df) or {}
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
                    # Track source file for each device
                    device_sources[_device_name] = device_file
                all_devices.update(file_devices)
            else:
                try:
                    with device_file.open("r", encoding="utf-8") as df:
                        device_yaml_config: dict[str, Any] = yaml.safe_load(df) or {}
                        file_devices_node = cast(
                            dict[str, dict[str, Any]],
                            device_yaml_config.get("devices", {}) or {},
                        )
                        # Apply defaults to YAML devices and collect into a typed dict
                        typed_file_devices: dict[str, dict[str, Any]] = {}
                        for _device_name, device_dict in file_devices_node.items():
                            # Apply defaults
                            for key, default_value in device_defaults.items():
                                if key not in device_dict:
                                    device_dict[key] = default_value
                            # Ensure a valid device_type default for YAML devices
                            device_dict.setdefault("device_type", "linux")
                            # Track source file for each device
                            device_sources[_device_name] = device_file
                            typed_file_devices[_device_name] = device_dict
                        all_devices.update(typed_file_devices)
                except yaml.YAMLError as e:
                    logging.warning(f"Invalid YAML in {device_file}: {e}")

        # Enhanced group loading with CSV support and subdirectory discovery
        all_groups: dict[str, Any] = {}
        group_files = _discover_config_files(config_dir, "groups")
        group_sources: dict[str, Path] = {}

        for group_file in group_files:
            if group_file.suffix.lower() == ".csv":
                file_groups = _load_csv_groups(group_file)
                # Track source per group name
                for _group_name in file_groups.keys():
                    group_sources[_group_name] = group_file
                all_groups.update(file_groups)
            else:
                try:
                    with group_file.open("r", encoding="utf-8") as gf:
                        group_yaml_config: dict[str, Any] = yaml.safe_load(gf) or {}
                        file_groups_node = cast(
                            dict[str, dict[str, Any]],
                            group_yaml_config.get("groups", {}) or {},
                        )
                        for _group_name in file_groups_node.keys():
                            group_sources[_group_name] = group_file
                        all_groups.update(file_groups_node)
                except yaml.YAMLError as e:
                    logging.warning(f"Invalid YAML in {group_file}: {e}")

        # Load vendor-specific sequences from config files
        sequence_files = _discover_config_files(config_dir, "sequences")
        sequences_config: dict[str, Any] = {}

        for seq_file in sequence_files:
            if (
                seq_file.suffix.lower() != ".csv"
            ):  # Only process YAML files for vendor config
                try:
                    with seq_file.open("r", encoding="utf-8") as sf:
                        seq_yaml_config: dict[str, Any] = yaml.safe_load(sf) or {}

                        # Keep track of other sequence config for vendor sequences
                        if not sequences_config:
                            sequences_config = seq_yaml_config
                        else:
                            sequences_config = _merge_configs(
                                sequences_config, seq_yaml_config
                            )
                except yaml.YAMLError as e:
                    logging.warning(f"Invalid YAML in {seq_file}: {e}")

        # Load vendor-specific sequences (VendorSequence models will carry _source_path)
        vendor_sequences = _load_vendor_sequences(config_dir, sequences_config)

        # Load global command sequences (vendor-agnostic)
        # Check both sequences_config (from sequences/ files) and main_config (inline)
        global_sequences_raw = sequences_config.get("sequences", {})
        if not global_sequences_raw and "global_command_sequences" in main_config:
            # Also support global_command_sequences key directly in main config
            global_sequences_raw = main_config.get("global_command_sequences", {})

        global_command_sequences: dict[str, VendorSequence] = {}
        if global_sequences_raw:
            # Convert raw dict to VendorSequence objects
            for seq_name, seq_data in global_sequences_raw.items():
                if isinstance(seq_data, dict):
                    global_command_sequences[seq_name] = VendorSequence(**seq_data)
                elif isinstance(seq_data, list):
                    # Support simple list of commands
                    global_command_sequences[seq_name] = VendorSequence(
                        description=f"Global sequence: {seq_name}",
                        commands=seq_data,
                    )

        # Merge inline devices/groups from main config with discovered files
        # Inline definitions from main config file
        inline_devices = main_config.get("devices", {})
        inline_groups = main_config.get("device_groups", {}) or main_config.get(
            "groups", {}
        )

        # Track source paths for inline devices/groups
        for device_name in inline_devices:
            if device_name not in device_sources:
                device_sources[device_name] = config_file

        for group_name in inline_groups:
            if group_name not in group_sources:
                group_sources[group_name] = config_file

        # Merge: discovered files take precedence over inline (override behavior)
        final_devices = {**inline_devices, **all_devices}
        final_groups = {**inline_groups, **all_groups}

        # Merge all configs into the expected format
        merged_config: dict[str, Any] = {
            "general": main_config.get("general", {}),
            "devices": final_devices,
            "device_groups": final_groups,
            "vendor_platforms": sequences_config.get("vendor_platforms", {}),
            "vendor_sequences": vendor_sequences,
            "global_command_sequences": (
                global_command_sequences if global_command_sequences else None
            ),
        }

        logging.debug(f"Loaded modular configuration from {config_dir.resolve()}")
        logging.debug(f"  - Devices: {len(all_devices)}")
        logging.debug(f"  - Groups: {len(all_groups)}")

        # Build the model and then assign private source paths
        model = NetworkConfig(**merged_config)

        if model.devices:
            # Persist source on each device instance (private attr via setter)
            for _name, _dev in model.devices.items():
                src = device_sources.get(_name)
                if src is not None:
                    _dev.set_source_path(src)

        if model.device_groups:
            for _name, _grp in model.device_groups.items():
                src = group_sources.get(_name)
                if src is not None:
                    _grp.set_source_path(src)

        return model

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
    """
    Load vendor-specific sequences from sequences directory.

    Uses explicit vendor_platforms configuration if available, otherwise
    auto-discovers vendor directories for backward compatibility and
    future-proof operation.
    """
    vendor_sequences: dict[str, dict[str, VendorSequence]] = {}

    # Get vendor platform configurations
    vendor_platforms = sequences_config.get("vendor_platforms", {})

    if vendor_platforms:
        # Use explicit vendor platform configuration (preferred)
        for platform_name, platform_config in vendor_platforms.items():
            platform_sequences = _load_vendor_platform_sequences(
                config_dir, platform_name, platform_config
            )
            if platform_sequences:
                vendor_sequences[platform_name] = platform_sequences
    else:
        # Auto-discovery fallback for backward compatibility
        vendor_sequences = _auto_discover_vendor_sequences(config_dir)
        if vendor_sequences:
            logging.debug(
                f"Auto-discovered {len(vendor_sequences)} vendor platforms "
                f"in {config_dir / 'sequences'}"
            )

    return vendor_sequences


def _load_vendor_platform_sequences(
    config_dir: Path, platform_name: str, platform_config: dict[str, Any]
) -> dict[str, VendorSequence]:
    """Load sequences for a specific vendor platform using explicit configuration."""
    platform_sequences: dict[str, VendorSequence] = {}

    # Build path to vendor sequences
    sequence_path = config_dir / platform_config.get("sequence_path", "")

    if not sequence_path.exists():
        logging.debug(f"Vendor sequence path not found: {sequence_path}")
        return platform_sequences

    # Load default sequence files for this vendor
    default_files = platform_config.get("default_files", ["common.yml"])

    for sequence_file in default_files:
        vendor_file_path = sequence_path / sequence_file

        if not vendor_file_path.exists():
            logging.debug(f"Vendor sequence file not found: {vendor_file_path}")
            continue

        sequences = _load_sequence_file(vendor_file_path, platform_name)
        platform_sequences.update(sequences)

    return platform_sequences


def _auto_discover_vendor_sequences(
    config_dir: Path,
) -> dict[str, dict[str, VendorSequence]]:
    """
    Auto-discover vendor sequences by scanning the sequences directory.

    This provides backward compatibility when vendor_platforms is not configured
    and future-proofs against missing configuration.
    """
    vendor_sequences: dict[str, dict[str, VendorSequence]] = {}
    sequences_dir = config_dir / "sequences"

    if not sequences_dir.exists():
        logging.debug(f"Sequences directory not found: {sequences_dir}")
        return vendor_sequences

    # Scan for vendor subdirectories
    for vendor_dir in sequences_dir.iterdir():
        if not vendor_dir.is_dir() or vendor_dir.name.startswith("."):
            continue

        vendor_name = vendor_dir.name
        platform_sequences: dict[str, VendorSequence] = {}

        # Look for common sequence files
        sequence_files = [
            "common.yml",
            "common.yaml",
            f"{vendor_name}.yml",
            f"{vendor_name}.yaml",
        ]

        for sequence_file in sequence_files:
            vendor_file_path = vendor_dir / sequence_file
            if vendor_file_path.exists():
                sequences = _load_sequence_file(vendor_file_path, vendor_name)
                platform_sequences.update(sequences)
                break  # Use first found file

        # Also scan for any other YAML files in the vendor directory
        for yaml_file in vendor_dir.glob("*.yml"):
            if yaml_file.name not in sequence_files:
                sequences = _load_sequence_file(yaml_file, vendor_name)
                platform_sequences.update(sequences)

        for yaml_file in vendor_dir.glob("*.yaml"):
            if yaml_file.name not in sequence_files:
                sequences = _load_sequence_file(yaml_file, vendor_name)
                platform_sequences.update(sequences)

        if platform_sequences:
            vendor_sequences[vendor_name] = platform_sequences
            logging.debug(
                f"Auto-discovered {len(platform_sequences)} sequences for {vendor_name}"
            )

    return vendor_sequences


def _load_sequence_file(file_path: Path, vendor_name: str) -> dict[str, VendorSequence]:
    """Load sequences from a single vendor sequence file."""
    sequences: dict[str, VendorSequence] = {}

    try:
        with file_path.open("r", encoding="utf-8") as f:
            vendor_config: dict[str, Any] = yaml.safe_load(f) or {}
        # Load sequences from the vendor file
        sequence_data = cast(
            dict[str, dict[str, Any]], vendor_config.get("sequences", {}) or {}
        )
        for seq_name, seq_data in sequence_data.items():
            try:
                seq_obj = VendorSequence(**seq_data)
                # Store source path on the sequence object (private via setter)
                seq_obj.set_source_path(file_path)
                sequences[seq_name] = seq_obj
            except Exception as e:
                logging.warning(f"Invalid sequence '{seq_name}' in {file_path}: {e}")
                continue

        logging.debug(
            f"Loaded {len(sequence_data)} sequences for {vendor_name} from {file_path}"
        )

    except yaml.YAMLError as e:
        logging.warning(f"Invalid YAML in vendor sequence file {file_path}: {e}")
    except Exception as e:  # pragma: no cover - robustness
        logging.warning(f"Failed to load vendor sequence file {file_path}: {e}")

    return sequences


# Legacy single-file YAML mode removed: no legacy loader remains


def generate_json_schema() -> dict[str, Any]:
    """
    Generate JSON schema for the NetworkConfig model.

    This can be used by YAML editors to provide validation and auto-completion.

    Returns
    -------
    dict[str, Any]
        JSON schema for NetworkConfig

    Examples
    --------
    Save schema to file for VS Code YAML extension:

    >>> import json
    >>> from pathlib import Path
    >>> schema = generate_json_schema()
    >>> Path("config-schema.json").write_text(json.dumps(schema, indent=2))
    """
    return NetworkConfig.model_json_schema()


def export_schemas_to_workspace() -> None:
    """
    Export JSON schemas to current workspace for editor integration.

    Creates:
    - schemas/network-config.schema.json (full config)
    - schemas/device-config.schema.json (device only)
    - .vscode/settings.json (VS Code YAML validation)

    This is automatically called by CLI commands when working in a project.
    """
    import json
    from pathlib import Path

    # Generate schemas
    full_schema = generate_json_schema()

    # Create schema directory
    schema_dir = Path("schemas")
    schema_dir.mkdir(exist_ok=True)

    # Full NetworkConfig schema
    full_schema_path = schema_dir / "network-config.schema.json"
    with full_schema_path.open("w", encoding="utf-8") as f:
        json.dump(full_schema, f, indent=2)

    # Extract DeviceConfig schema for standalone device files
    # Device files contain a "devices" object with multiple DeviceConfig entries
    device_collection_schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Device Collection Configuration",
        "description": "Schema for device collection files (config/devices/*.yml)",
        "type": "object",
        "properties": {
            "devices": {
                "type": "object",
                "additionalProperties": {"$ref": "#/$defs/DeviceConfig"},
                "description": "Dictionary of device configurations keyed by device name",
            }
        },
        "required": ["devices"],
        "$defs": full_schema["$defs"],  # Include all definitions for references
    }

    device_schema_path = schema_dir / "device-config.schema.json"
    with device_schema_path.open("w", encoding="utf-8") as f:
        json.dump(device_collection_schema, f, indent=2)

    # Create groups collection schema for standalone group files
    # Group files contain a "groups" object with multiple DeviceGroup entries
    groups_collection_schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Groups Collection Configuration",
        "description": "Schema for group collection files (config/groups/*.yml)",
        "type": "object",
        "properties": {
            "groups": {
                "type": "object",
                "additionalProperties": {"$ref": "#/$defs/DeviceGroup"},
                "description": "Dictionary of device group configurations keyed by group name",
            }
        },
        "required": ["groups"],
        "$defs": full_schema["$defs"],  # Include all definitions for references
    }

    groups_schema_path = schema_dir / "groups-config.schema.json"
    with groups_schema_path.open("w", encoding="utf-8") as f:
        json.dump(groups_collection_schema, f, indent=2)

    # Create/update VS Code settings for YAML validation
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    settings_path = vscode_dir / "settings.json"
    yaml_schema_config = {
        "yaml.schemas": {
            "./schemas/network-config.schema.json": [
                "config/config.yml",
                "devices.yml",
            ],
            "./schemas/device-config.schema.json": [
                "config/devices/*.yml",
                "config/devices.yml",
            ],
            "./schemas/groups-config.schema.json": [
                "config/groups/*.yml",
                "config/groups.yml",
            ],
        }
    }

    # Merge with existing settings if they exist
    if settings_path.exists():
        try:
            with settings_path.open("r", encoding="utf-8") as f:
                existing_settings = json.load(f)
            # Only update yaml.schemas, preserve other settings
            existing_settings.update(yaml_schema_config)
            yaml_schema_config = existing_settings
        except (json.JSONDecodeError, KeyError):
            # If existing settings are malformed, just use our config
            pass

    with settings_path.open("w", encoding="utf-8") as f:
        json.dump(yaml_schema_config, f, indent=2)

    logging.debug(f"Exported schemas to {schema_dir.resolve()}")
    logging.debug(f"Updated VS Code settings at {settings_path.resolve()}")


def get_supported_device_types() -> set[str]:
    """
    Get the set of supported device types for validation.

    Returns
    -------
    set[str]
        Set of supported device type strings
    """
    # Extract from the Literal type for consistency
    return {
        "mikrotik_routeros",
        "cisco_iosxe",
        "cisco_ios",
        "cisco_iosxr",
        "cisco_nxos",
        "juniper_junos",
        "arista_eos",
        "nokia_srlinux",
        "linux",
        "generic",
    }
