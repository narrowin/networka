# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for configuration management."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from network_toolkit.config import (
    CommandSequence,
    DeviceConfig,
    DeviceGroup,
    DeviceOverrides,
    FileOperationConfig,
    GeneralConfig,
    NetworkConfig,
    VendorPlatformConfig,
    VendorSequence,
    get_env_credential,
    load_config,
    load_dotenv_files,
)
from network_toolkit.exceptions import NetworkToolkitError


class TestGeneralConfig:
    """Test GeneralConfig model validation."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        # Set up environment variables for testing
        os.environ["NT_DEFAULT_USER"] = "admin"
        os.environ["NT_DEFAULT_PASSWORD"] = "admin"

        config = GeneralConfig()
        assert config.firmware_dir == "/tmp/firmware"
        assert config.backup_dir == "/tmp/backups"
        assert config.default_user == "admin"
        assert config.default_password == "admin"
        assert config.transport == "ssh"
        assert config.port == 22
        assert config.timeout == 30
        assert config.connection_retries == 3
        assert config.retry_delay == 5
        assert config.transfer_timeout == 300
        assert config.verify_checksums is True
        assert config.command_timeout == 60
        assert config.enable_logging is True
        assert config.log_level == "INFO"
        assert config.backup_retention_days == 30
        assert config.max_backups_per_device == 10
        assert config.store_results is False
        assert config.results_format == "txt"
        assert config.results_include_timestamp is True
        assert config.results_include_command is True

    def test_results_format_validation(self) -> None:
        """Test results format validation."""
        # Valid formats
        for fmt in ["txt", "json", "yaml", "TXT", "JSON", "YAML"]:
            config = GeneralConfig(results_format=fmt)
            assert config.results_format == fmt.lower()

        # Invalid format
        with pytest.raises(Exception, match="results_format must be one of"):
            GeneralConfig(results_format="xml")

    def test_transport_validation(self) -> None:
        """Test transport validation."""
        # Valid transports
        for transport in ["ssh", "telnet", "SSH", "TELNET"]:
            config = GeneralConfig(transport=transport)
            assert config.transport == transport.lower()

        # Invalid transport
        with pytest.raises(Exception, match="transport must be either"):
            GeneralConfig(transport="http")

    def test_log_level_validation(self) -> None:
        """Test log level validation."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "debug"]:
            config = GeneralConfig(log_level=level)
            assert config.log_level == level.upper()

        # Invalid log level
        with pytest.raises(Exception, match="log_level must be one of"):
            GeneralConfig(log_level="INVALID")


class TestDeviceOverrides:
    """Test DeviceOverrides model."""

    def test_empty_overrides(self) -> None:
        """Test empty overrides."""
        overrides = DeviceOverrides()
        assert overrides.user is None
        assert overrides.password is None
        assert overrides.port is None
        assert overrides.timeout is None
        assert overrides.transport is None
        assert overrides.command_timeout is None
        assert overrides.transfer_timeout is None

    def test_override_values(self) -> None:
        """Test setting override values."""
        overrides = DeviceOverrides(
            user="testuser",
            password="testpass",
            port=2222,
            timeout=60,
            transport="telnet",
            command_timeout=120,
            transfer_timeout=600,
        )
        assert overrides.user == "testuser"
        assert overrides.password == "testpass"
        assert overrides.port == 2222
        assert overrides.timeout == 60
        assert overrides.transport == "telnet"
        assert overrides.command_timeout == 120
        assert overrides.transfer_timeout == 600


class TestDeviceConfig:
    """Test DeviceConfig model."""

    def test_minimal_device_config(self) -> None:
        """Test minimal device configuration."""
        config = DeviceConfig(host="192.168.1.1")
        assert config.host == "192.168.1.1"
        assert config.description is None
        assert config.device_type == "mikrotik_routeros"
        assert config.model is None
        assert config.platform is None
        assert config.location is None
        assert config.user is None
        assert config.password is None
        assert config.port is None
        assert config.tags is None
        assert config.overrides is None
        assert config.command_sequences is None

    def test_full_device_config(self) -> None:
        """Test full device configuration."""
        overrides = DeviceOverrides(timeout=60)
        sequences = {"test": ["command1", "command2"]}

        config = DeviceConfig(
            host="192.168.1.1",
            description="Test device",
            device_type="cisco_ios",
            model="C2960",
            platform="arm",
            location="Lab",
            user="admin",
            password="secret",
            port=2222,
            tags=["switch", "test"],
            overrides=overrides,
            command_sequences=sequences,
        )

        assert config.host == "192.168.1.1"
        assert config.description == "Test device"
        assert config.device_type == "cisco_ios"
        assert config.model == "C2960"
        assert config.platform == "arm"
        assert config.location == "Lab"
        assert config.user == "admin"
        assert config.password == "secret"
        assert config.port == 2222
        assert config.tags == ["switch", "test"]
        assert config.overrides == overrides
        assert config.command_sequences == sequences


class TestDeviceGroup:
    """Test DeviceGroup model."""

    def test_device_group_members_only(self) -> None:
        """Test device group with members only."""
        group = DeviceGroup(description="Test group", members=["device1", "device2"])
        assert group.description == "Test group"
        assert group.members == ["device1", "device2"]
        assert group.match_tags is None

    def test_device_group_tags_only(self) -> None:
        """Test device group with tags only."""
        group = DeviceGroup(description="Test group", match_tags=["switch", "router"])
        assert group.description == "Test group"
        assert group.members is None
        assert group.match_tags == ["switch", "router"]

    def test_device_group_both(self) -> None:
        """Test device group with both members and tags."""
        group = DeviceGroup(description="Test group", members=["device1"], match_tags=["switch"])
        assert group.description == "Test group"
        assert group.members == ["device1"]
        assert group.match_tags == ["switch"]


class TestCommandSequence:
    """Test CommandSequence model."""

    def test_command_sequence(self) -> None:
        """Test command sequence creation."""
        sequence = CommandSequence(description="Test sequence", commands=["command1", "command2", "command3"])
        assert sequence.description == "Test sequence"
        assert sequence.commands == ["command1", "command2", "command3"]


class TestFileOperationConfig:
    """Test FileOperationConfig model."""

    def test_empty_file_operation(self) -> None:
        """Test empty file operation config."""
        config = FileOperationConfig()
        assert config.local_path is None
        assert config.remote_path is None
        assert config.verify_checksum is None
        assert config.backup_before_upgrade is None
        assert config.remote_files is None
        assert config.compress is None
        assert config.file_pattern is None

    def test_full_file_operation(self) -> None:
        """Test full file operation config."""
        config = FileOperationConfig(
            local_path="/local/file.txt",
            remote_path="/remote/file.txt",
            verify_checksum=True,
            backup_before_upgrade=True,
            remote_files=["file1.txt", "file2.txt"],
            compress=True,
            file_pattern="*.txt",
        )
        assert config.local_path == "/local/file.txt"
        assert config.remote_path == "/remote/file.txt"
        assert config.verify_checksum is True
        assert config.backup_before_upgrade is True
        assert config.remote_files == ["file1.txt", "file2.txt"]
        assert config.compress is True
        assert config.file_pattern == "*.txt"


class TestNetworkConfig:
    """Test NetworkConfig model and methods."""

    def test_empty_network_config(self) -> None:
        """Test empty network configuration."""
        config = NetworkConfig()
        assert isinstance(config.general, GeneralConfig)
        assert config.devices is None
        assert config.device_groups is None
        assert config.global_command_sequences is None
        assert config.file_operations is None

    def test_get_device_connection_params_nonexistent_device(self) -> None:
        """Test getting connection params for nonexistent device."""
        config = NetworkConfig()
        with pytest.raises(ValueError, match="Device 'nonexistent' not found"):
            config.get_device_connection_params("nonexistent")

    def test_get_device_connection_params_basic(self, sample_config: NetworkConfig) -> None:
        """Test getting basic device connection parameters."""
        params = sample_config.get_device_connection_params("test_device1")

        expected = {
            "host": "192.168.1.10",
            "auth_username": "admin",
            "auth_password": "testpass",
            "port": 22,
            "timeout_socket": 30,
            "timeout_transport": 30,
            "transport": "ssh",
            "platform": "mipsbe",
        }

        assert params == expected

    def test_get_device_connection_params_with_overrides(self, sample_config: NetworkConfig) -> None:
        """Test getting device connection parameters with overrides."""
        params = sample_config.get_device_connection_params("test_device2")

        expected = {
            "host": "192.168.1.20",
            "auth_username": "testuser",
            "auth_password": "testpass2",
            "port": 2222,
            "timeout_socket": 60,
            "timeout_transport": 60,
            "transport": "ssh",
            "platform": "mikrotik_routeros",
        }

        assert params == expected

    def test_get_group_members_nonexistent_group(self, sample_config: NetworkConfig) -> None:
        """Test getting members of nonexistent group."""
        with pytest.raises(NetworkToolkitError, match="Device group 'nonexistent'"):
            sample_config.get_group_members("nonexistent")

    def test_get_group_members_direct_members(self, sample_config: NetworkConfig) -> None:
        """Test getting group members from direct member list."""
        members = sample_config.get_group_members("lab_devices")
        assert set(members) == {"test_device1", "test_device2"}

    def test_get_group_members_tag_based(self, sample_config: NetworkConfig) -> None:
        """Test getting group members from tag matching."""
        members = sample_config.get_group_members("all_switches")
        assert set(members) == {"test_device1", "test_device3"}

    def test_get_group_members_combined(self, sample_config: NetworkConfig) -> None:
        """Test getting group members from both members and tags."""
        members = sample_config.get_group_members("core_network")
        # Should include test_device2 from members list
        assert "test_device2" in members
        # Should not duplicate devices
        assert len(members) == len(set(members))


class TestLoadConfig:
    """Test configuration loading functionality."""

    def test_load_config_success(self, config_file: Path) -> None:
        """Test successful configuration loading."""
        config = load_config(config_file)
        assert isinstance(config, NetworkConfig)
        assert config.devices is not None
        assert "test_device1" in config.devices
        assert config.device_groups is not None
        assert "all_switches" in config.device_groups

    def test_load_config_file_not_found(self, temp_dir: Path) -> None:
        """Test loading nonexistent configuration file."""
        nonexistent_file = temp_dir / "nonexistent.yml"
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(nonexistent_file)

    def test_load_config_invalid_yaml(self, invalid_config_file: Path) -> None:
        """Test loading invalid YAML configuration."""
        with pytest.raises(ValueError, match="Invalid YAML in configuration file"):
            load_config(invalid_config_file)

    def test_load_config_empty_file(self, temp_dir: Path) -> None:
        """Test loading empty configuration file."""
        empty_file = temp_dir / "empty.yml"
        empty_file.write_text("")

        config = load_config(empty_file)
        assert isinstance(config, NetworkConfig)
        assert isinstance(config.general, GeneralConfig)

    def test_load_config_with_validation_error(self, temp_dir: Path) -> None:
        """Test loading configuration with validation errors."""
        invalid_data = {"general": {"results_format": "invalid_format"}}

        invalid_file = temp_dir / "invalid_data.yml"
        with invalid_file.open("w") as f:
            yaml.dump(invalid_data, f)

        with pytest.raises(Exception, match="Failed to load configuration"):
            load_config(invalid_file)

    def test_load_config_string_path(self, config_file: Path) -> None:
        """Test loading configuration with string path."""
        config = load_config(str(config_file))
        assert isinstance(config, NetworkConfig)

    def test_load_config_path_object(self, config_file: Path) -> None:
        """Test loading configuration with Path object."""
        config = load_config(config_file)
        assert isinstance(config, NetworkConfig)


class TestDeviceConfigValidation:
    """Test DeviceConfig validation and edge cases."""

    def test_device_config_minimal(self) -> None:
        """Test device config with minimal required fields."""
        device = DeviceConfig(host="192.168.1.1")
        assert device.host == "192.168.1.1"
        assert device.device_type == "mikrotik_routeros"  # Default value
        assert device.description is None
        assert device.port is None  # Uses general config default

    def test_device_config_all_fields(self) -> None:
        """Test device config with all fields specified."""
        overrides = DeviceOverrides(
            user="override_user",
            password="override_pass",
            port=2222,
            timeout=120,
        )

        device = DeviceConfig(
            host="192.168.1.1",
            description="Test device",
            device_type="mikrotik_routeros",
            model="RB4011",
            platform="RouterOS",
            location="Datacenter",
            user="cisco",
            password="cisco",
            port=2222,
            tags=["routers", "core"],
            overrides=overrides,
            command_sequences={"test": ["command1", "command2"]},
        )
        assert device.host == "192.168.1.1"
        assert device.description == "Test device"
        assert device.device_type == "mikrotik_routeros"
        assert device.model == "RB4011"
        assert device.platform == "RouterOS"
        assert device.location == "Datacenter"
        assert device.user == "cisco"
        assert device.password == "cisco"
        assert device.port == 2222
        assert device.tags == ["routers", "core"]
        assert device.overrides == overrides
        assert device.command_sequences == {"test": ["command1", "command2"]}

    def test_device_config_with_overrides(self) -> None:
        """Test device config with overrides object."""
        overrides = DeviceOverrides(
            user="override_user",
            timeout=300,
            transport="telnet",
        )

        device = DeviceConfig(
            host="192.168.1.10",
            overrides=overrides,
        )

        assert device.host == "192.168.1.10"
        assert device.overrides is not None
        assert device.overrides.user == "override_user"
        assert device.overrides.timeout == 300
        assert device.overrides.transport == "telnet"


class TestGeneralConfigValidation:
    """Test GeneralConfig validation and edge cases."""

    def test_general_config_defaults(self) -> None:
        """Test general config with default values."""
        config = GeneralConfig()
        assert config.transport == "ssh"
        assert config.port == 22
        assert config.timeout == 30
        assert config.verify_checksums is True
        assert config.store_results is False

    def test_general_config_custom_values(self) -> None:
        """Test general config with custom values."""
        config = GeneralConfig(
            transport="telnet",
            port=23,
            timeout=60,
            connection_retries=5,
            retry_delay=10,
        )
        assert config.transport == "telnet"
        assert config.port == 23
        assert config.timeout == 60
        assert config.connection_retries == 5
        assert config.retry_delay == 10

    def test_general_config_invalid_transport(self) -> None:
        """Test general config with invalid transport."""
        with pytest.raises(ValueError, match="transport must be either 'ssh' or 'telnet'"):
            GeneralConfig(transport="invalid")

    def test_general_config_invalid_log_level(self) -> None:
        """Test general config with invalid log level."""
        with pytest.raises(ValueError, match="log_level must be one of"):
            GeneralConfig(log_level="INVALID")

    def test_general_config_results_format_validation(self) -> None:
        """Test general config results format validation."""
        # Valid formats
        for fmt in ["txt", "json", "yaml"]:
            config = GeneralConfig(results_format=fmt)
            assert config.results_format == fmt.lower()

        # Invalid format
        with pytest.raises(ValueError, match="results_format must be one of"):
            GeneralConfig(results_format="invalid")


class TestDeviceOverridesExtended:
    """Test DeviceOverrides extended functionality."""

    def test_device_overrides_partial(self) -> None:
        """Test creating partial device overrides."""
        overrides = DeviceOverrides(user="partial_user")
        assert overrides.user == "partial_user"
        assert overrides.password is None
        assert overrides.port is None
        assert overrides.timeout is None

    def test_device_overrides_all_fields(self) -> None:
        """Test creating device overrides with all fields."""
        overrides = DeviceOverrides(
            user="test_user",
            password="test_pass",
            port=2222,
            timeout=120,
            transport="telnet",
            command_timeout=90,
            transfer_timeout=600,
        )
        assert overrides.user == "test_user"
        assert overrides.password == "test_pass"
        assert overrides.port == 2222
        assert overrides.timeout == 120
        assert overrides.transport == "telnet"
        assert overrides.command_timeout == 90
        assert overrides.transfer_timeout == 600


class TestDeviceGroupExtended:
    """Test DeviceGroup extended functionality."""

    def test_device_group_creation(self) -> None:
        """Test creating device groups."""
        group = DeviceGroup(
            description="Test group",
            members=["device1", "device2", "device3"],
            match_tags=["switch", "production"],
        )
        assert group.description == "Test group"
        assert group.members == ["device1", "device2", "device3"]
        assert group.match_tags == ["switch", "production"]

    def test_device_group_minimal(self) -> None:
        """Test creating minimal device group."""
        group = DeviceGroup(description="Minimal group")
        assert group.description == "Minimal group"
        assert group.members is None
        assert group.match_tags is None


class TestCommandSequenceExtended:
    """Test CommandSequence extended functionality."""

    def test_command_sequence_creation(self) -> None:
        """Test creating command sequences."""
        sequence = CommandSequence(
            description="Test sequence",
            commands=["command1", "command2"],
            tags=["system", "info"],
        )
        assert sequence.description == "Test sequence"
        assert sequence.commands == ["command1", "command2"]
        assert sequence.tags == ["system", "info"]

    def test_command_sequence_minimal(self) -> None:
        """Test creating minimal command sequence."""
        sequence = CommandSequence(
            description="Minimal sequence",
            commands=["single_command"],
        )
        assert sequence.description == "Minimal sequence"
        assert sequence.commands == ["single_command"]
        assert sequence.tags is None


class TestVendorPlatformConfig:
    """Test VendorPlatformConfig functionality."""

    def test_vendor_platform_config_creation(self) -> None:
        """Test creating vendor platform config."""
        config = VendorPlatformConfig(
            description="Cisco IOS XE Support",
            sequence_path="/path/to/cisco_iosxe",
            default_files=["common.yml", "interfaces.yml"],
        )
        assert config.description == "Cisco IOS XE Support"
        assert config.sequence_path == "/path/to/cisco_iosxe"
        assert config.default_files == ["common.yml", "interfaces.yml"]

    def test_vendor_platform_config_defaults(self) -> None:
        """Test vendor platform config with defaults."""
        config = VendorPlatformConfig(
            description="Basic Support",
            sequence_path="/path/to/basic",
        )
        assert config.description == "Basic Support"
        assert config.sequence_path == "/path/to/basic"
        assert config.default_files == ["common.yml"]


class TestVendorSequence:
    """Test VendorSequence functionality."""

    def test_vendor_sequence_creation(self) -> None:
        """Test creating vendor sequences."""
        sequence = VendorSequence(
            description="System info sequence",
            category="system",
            timeout=60,
            device_types=["mikrotik_routeros"],
            commands=["/system identity print", "/system clock print"],
        )
        assert sequence.description == "System info sequence"
        assert sequence.category == "system"
        assert sequence.timeout == 60
        assert sequence.device_types == ["mikrotik_routeros"]
        assert sequence.commands == ["/system identity print", "/system clock print"]

    def test_vendor_sequence_minimal(self) -> None:
        """Test creating minimal vendor sequence."""
        sequence = VendorSequence(
            description="Minimal sequence",
            commands=["single command"],
        )
        assert sequence.description == "Minimal sequence"
        assert sequence.commands == ["single command"]
        assert sequence.category is None
        assert sequence.timeout is None


class TestNetworkConfigValidation:
    """Test NetworkConfig validation and complex scenarios."""

    def test_network_config_device_validation(self, tmp_path: Path) -> None:
        """Test network config with invalid device type loads successfully."""
        config_file = tmp_path / "invalid_device.yml"
        config_data = {
            "general": {
                "default_user": "admin",
                "default_password": "admin",
            },
            "devices": {
                "invalid_device": {
                    "host": "192.168.1.1",
                    "device_type": "invalid_type",  # Invalid device type
                }
            },
        }
        config_file.write_text(yaml.safe_dump(config_data))

        # Config should load successfully - validation happens at runtime
        config = load_config(config_file)
        assert config.devices is not None
        assert "invalid_device" in config.devices
        assert config.devices["invalid_device"].device_type == "invalid_type"

    def test_network_config_missing_credentials(self, tmp_path: Path) -> None:
        """Test network config missing credentials loads but fails at runtime."""
        config_file = tmp_path / "no_credentials.yml"
        config_data = {
            "general": {},  # No default credentials
            "devices": {
                "test_device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                }
            },
        }
        config_file.write_text(yaml.safe_dump(config_data))

        # Clear environment variables to ensure no fallback
        old_user = os.environ.get("NT_DEFAULT_USER")
        old_pass = os.environ.get("NT_DEFAULT_PASSWORD")

        if "NT_DEFAULT_USER" in os.environ:
            del os.environ["NT_DEFAULT_USER"]
        if "NT_DEFAULT_PASSWORD" in os.environ:
            del os.environ["NT_DEFAULT_PASSWORD"]

        try:
            # Config should load successfully - credential validation happens at runtime
            config = load_config(config_file)
            assert config.devices is not None
            assert "test_device" in config.devices

            # But accessing default_user/default_password properties should fail
            with pytest.raises(ValueError, match="Default username not found"):
                _ = config.general.default_user

            with pytest.raises(ValueError, match="Default password not found"):
                _ = config.general.default_password

        finally:
            # Restore environment variables
            if old_user is not None:
                os.environ["NT_DEFAULT_USER"] = old_user
            if old_pass is not None:
                os.environ["NT_DEFAULT_PASSWORD"] = old_pass

    def test_network_config_device_group_references(self, tmp_path: Path) -> None:
        """Test network config with device group references."""
        config_file = tmp_path / "groups.yml"
        config_data = {
            "general": {
                "default_user": "admin",
                "default_password": "admin",
            },
            "devices": {
                "device1": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                },
                "device2": {
                    "host": "192.168.1.2",
                    "device_type": "mikrotik_routeros",
                },
            },
            "device_groups": {
                "switches": {
                    "description": "All switches",
                    "members": ["device1"],
                },
                "routers": {
                    "description": "All routers",
                    "members": ["device2"],
                },
            },
        }
        config_file.write_text(yaml.safe_dump(config_data))

        config = load_config(config_file)
        assert config.device_groups is not None
        assert "switches" in config.device_groups
        assert "routers" in config.device_groups
        assert config.device_groups["switches"].members == ["device1"]
        assert config.device_groups["routers"].members == ["device2"]

    def test_network_config_sequences(self, tmp_path: Path) -> None:
        """Test network config with command sequences."""
        config_file = tmp_path / "sequences.yml"
        config_data = {
            "general": {
                "default_user": "admin",
                "default_password": "admin",
            },
            "devices": {
                "test_device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                }
            },
            "global_command_sequences": {
                "system_info": {
                    "description": "Get system information",
                    "commands": [
                        "/system identity print",
                        "/system clock print",
                    ],
                }
            },
        }
        config_file.write_text(yaml.safe_dump(config_data))

        config = load_config(config_file)
        assert config.global_command_sequences is not None
        assert "system_info" in config.global_command_sequences
        sequence = config.global_command_sequences["system_info"]
        assert sequence.description == "Get system information"
        assert len(sequence.commands) == 2

    def test_network_config_environment_variable_substitution(self, tmp_path: Path) -> None:
        """Test environment variable substitution in config."""
        # Set test environment variables
        os.environ["TEST_USER"] = "env_user"
        os.environ["TEST_PASSWORD"] = "env_password"
        os.environ["TEST_HOST"] = "192.168.100.1"

        config_file = tmp_path / "env_vars.yml"
        config_data = {
            "general": {
                "default_user": "admin",
                "default_password": "admin",
            },
            "devices": {
                "env_device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                }
            },
        }
        config_file.write_text(yaml.safe_dump(config_data))

        try:
            config = load_config(config_file)
            assert config.devices is not None
            assert config.devices["env_device"].host == "192.168.1.1"
        finally:
            # Clean up environment variables
            for key in ["TEST_USER", "TEST_PASSWORD", "TEST_HOST"]:
                if key in os.environ:
                    del os.environ[key]

    def test_network_config_file_operation_config(self, tmp_path: Path) -> None:
        """Test network config with file operation settings."""
        config_file = tmp_path / "file_ops.yml"
        config_data = {
            "general": {
                "default_user": "admin",
                "default_password": "admin",
                "verify_checksums": False,
                "transfer_timeout": 600,
            },
            "devices": {
                "test_device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                }
            },
            "file_operations": {
                "firmware_upload": {
                    "local_path": "/local/firmware",
                    "remote_path": "/remote/firmware",
                    "verify_checksum": True,
                    "backup_before_upgrade": True,
                }
            },
        }
        config_file.write_text(yaml.safe_dump(config_data))

        config = load_config(config_file)
        assert config.general.verify_checksums is False
        assert config.general.transfer_timeout == 600
        if config.file_operations:
            assert "firmware_upload" in config.file_operations
            file_op = config.file_operations["firmware_upload"]
            assert file_op.local_path == "/local/firmware"
            assert file_op.remote_path == "/remote/firmware"
            assert file_op.verify_checksum is True
            assert file_op.backup_before_upgrade is True


class TestModularConfigLoading:
    """Test modular configuration loading functionality."""

    def test_modular_config_basic(self, tmp_path: Path) -> None:
        """Test basic modular config loading."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create main config file
        config_file = config_dir / "config.yml"
        config_data = {
            "general": {
                "timeout": 45,
                "port": 2222,
            }
        }
        config_file.write_text(yaml.safe_dump(config_data))

        # Create devices file
        devices_file = config_dir / "devices.yml"
        devices_data = {
            "devices": {
                "test_device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                }
            }
        }
        devices_file.write_text(yaml.safe_dump(devices_data))

        # Load modular config
        config = load_config(config_dir)
        assert config.general.timeout == 45
        assert config.general.port == 2222
        assert config.devices is not None
        assert "test_device" in config.devices

    def test_modular_config_with_devices_directory(self, tmp_path: Path) -> None:
        """Test modular config with devices directory and defaults."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create main config
        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.safe_dump({"general": {"timeout": 30}}))

        # Create base devices file
        devices_file = config_dir / "devices.yml"
        devices_data = {
            "devices": {
                "base_device": {
                    "host": "192.168.1.100",
                    "device_type": "mikrotik_routeros",
                }
            }
        }
        devices_file.write_text(yaml.safe_dump(devices_data))

        # Create devices directory with defaults
        devices_dir = config_dir / "devices"
        devices_dir.mkdir()

        # Create defaults file
        defaults_file = devices_dir / "_defaults.yml"
        defaults_data = {
            "defaults": {
                "device_type": "cisco_iosxe",
                "port": 23,
            }
        }
        defaults_file.write_text(yaml.safe_dump(defaults_data))

        # Create additional device file
        device_fragment = devices_dir / "extra.yml"
        fragment_data = {
            "devices": {
                "extra_device": {
                    "host": "192.168.1.200",
                    "description": "Extra device with defaults",
                }
            }
        }
        device_fragment.write_text(yaml.safe_dump(fragment_data))

        # Load config
        config = load_config(config_dir)
        assert config.devices is not None
        assert "base_device" in config.devices
        assert "extra_device" in config.devices

        # Check that defaults were applied
        extra_device = config.devices["extra_device"]
        assert extra_device.host == "192.168.1.200"
        assert extra_device.device_type == "cisco_iosxe"  # From defaults
        assert extra_device.port == 23  # From defaults

    def test_modular_config_yaml_error_handling(self, tmp_path: Path) -> None:
        """Test YAML error handling in modular config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create valid main config
        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.safe_dump({"general": {"timeout": 30}}))

        # Create valid devices file
        devices_file = config_dir / "devices.yml"
        devices_file.write_text(yaml.safe_dump({"devices": {}}))

        # Create devices directory with invalid YAML
        devices_dir = config_dir / "devices"
        devices_dir.mkdir()

        # Invalid YAML in defaults
        defaults_file = devices_dir / "_defaults.yml"
        defaults_file.write_text("invalid: yaml: content: [")

        # Invalid YAML in device fragment
        fragment_file = devices_dir / "invalid.yml"
        fragment_file.write_text("devices:\n  test:\n    host: 192.168.1.1\n    invalid: [")

        # Should load successfully but skip invalid files
        config = load_config(config_dir)
        assert config.devices is not None

    def test_modular_config_invalid_structure(self, tmp_path: Path) -> None:
        """Test handling of invalid structure in device fragments."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.safe_dump({"general": {"timeout": 30}}))

        devices_file = config_dir / "devices.yml"
        devices_file.write_text(yaml.safe_dump({"devices": {}}))

        devices_dir = config_dir / "devices"
        devices_dir.mkdir()

        # Fragment with invalid structure (devices is not a dict)
        fragment_file = devices_dir / "invalid_structure.yml"
        fragment_data = {"devices": "not_a_dict"}
        fragment_file.write_text(yaml.safe_dump(fragment_data))

        # Should load successfully but skip invalid structure
        config = load_config(config_dir)
        assert config.devices is not None

    def test_modular_config_with_groups_and_sequences(self, tmp_path: Path) -> None:
        """Test modular config with groups and sequences files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create main config
        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.safe_dump({"general": {"timeout": 30}}))

        # Create devices
        devices_file = config_dir / "devices.yml"
        devices_data = {"devices": {"device1": {"host": "192.168.1.1", "device_type": "mikrotik_routeros"}}}
        devices_file.write_text(yaml.safe_dump(devices_data))

        # Create groups file
        groups_file = config_dir / "groups.yml"
        groups_data = {
            "groups": {
                "switches": {
                    "description": "All switches",
                    "members": ["device1"],
                }
            }
        }
        groups_file.write_text(yaml.safe_dump(groups_data))

        # Create sequences file
        sequences_file = config_dir / "sequences.yml"
        sequences_data = {
            "sequences": {
                "system_info": {
                    "description": "Get system info",
                    "commands": ["/system identity print"],
                }
            },
            "vendor_platforms": {
                "mikrotik_routeros": {
                    "description": "MikroTik RouterOS",
                    "sequence_path": "sequences/mikrotik_routeros",
                    "default_files": ["common.yml"],
                }
            },
        }
        sequences_file.write_text(yaml.safe_dump(sequences_data))

        # Create vendor sequence directory
        vendor_dir = config_dir / "sequences" / "mikrotik_routeros"
        vendor_dir.mkdir(parents=True)

        vendor_file = vendor_dir / "common.yml"
        vendor_data = {
            "sequences": {
                "system_check": {
                    "description": "System check sequence",
                    "commands": ["/system resource print", "/system clock print"],
                }
            }
        }
        vendor_file.write_text(yaml.safe_dump(vendor_data))

        # Load config
        config = load_config(config_dir)
        assert config.device_groups is not None
        assert "switches" in config.device_groups
        assert config.global_command_sequences is not None
        assert "system_info" in config.global_command_sequences
        assert config.vendor_sequences is not None
        assert "mikrotik_routeros" in config.vendor_sequences

    def test_modular_config_vendor_sequence_errors(self, tmp_path: Path) -> None:
        """Test vendor sequence loading with various error conditions."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.safe_dump({"general": {"timeout": 30}}))

        devices_file = config_dir / "devices.yml"
        devices_file.write_text(yaml.safe_dump({"devices": {}}))

        sequences_file = config_dir / "sequences.yml"
        sequences_data = {
            "vendor_platforms": {
                "nonexistent_platform": {
                    "description": "Non-existent platform",
                    "sequence_path": "nonexistent/path",
                },
                "invalid_yaml_platform": {
                    "description": "Platform with invalid YAML",
                    "sequence_path": "sequences/invalid",
                },
            }
        }
        sequences_file.write_text(yaml.safe_dump(sequences_data))

        # Create directory for invalid YAML test
        invalid_dir = config_dir / "sequences" / "invalid"
        invalid_dir.mkdir(parents=True)

        invalid_file = invalid_dir / "common.yml"
        invalid_file.write_text("sequences:\n  test:\n    invalid: [")

        # Should load successfully despite errors
        config = load_config(config_dir)
        assert config.vendor_sequences is not None

    def test_modular_config_missing_required_files(self, tmp_path: Path) -> None:
        """Test error handling when required files are missing."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Missing config.yml - should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="Main config file not found"):
            load_config(config_dir)

        # Create config.yml - should work even without other files (they're optional now)
        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.safe_dump({"general": {"timeout": 30}}))

        # This should work now - devices, groups, sequences are optional
        config = load_config(config_dir)
        assert config.general.timeout == 30
        assert config.devices == {}  # Empty devices is okay
        assert config.device_groups == {}  # Empty groups is okay

    def test_legacy_config_error_handling(self, tmp_path: Path) -> None:
        """Test error handling in legacy config loading."""
        # Invalid YAML file
        invalid_file = tmp_path / "invalid.yml"
        invalid_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ValueError, match="Invalid YAML in configuration file"):
            load_config(invalid_file)

        # Valid YAML but create a file that will cause NetworkConfig validation to fail
        # Use an empty file which should work fine
        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")

        # This should actually load successfully with empty config
        config = load_config(empty_file)
        assert isinstance(config, NetworkConfig)


class TestNetworkConfigAdvancedMethods:
    """Test advanced NetworkConfig methods."""

    def test_get_all_sequences_global_only(self) -> None:
        """Test get_all_sequences with only global sequences."""
        config = NetworkConfig(
            global_command_sequences={
                "global_seq": CommandSequence(
                    description="Global sequence",
                    commands=["cmd1", "cmd2"],
                )
            }
        )

        sequences = config.get_all_sequences()
        assert "global_seq" in sequences
        assert sequences["global_seq"]["origin"] == "global"
        assert sequences["global_seq"]["commands"] == ["cmd1", "cmd2"]
        assert sequences["global_seq"]["sources"] == ["global"]
        assert sequences["global_seq"]["description"] == "Global sequence"

    def test_get_all_sequences_device_only(self) -> None:
        """Test get_all_sequences with only device sequences."""
        config = NetworkConfig(
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1",
                    command_sequences={
                        "device_seq": ["cmd3", "cmd4"],
                        "shared_seq": ["cmd5"],
                    },
                ),
                "device2": DeviceConfig(
                    host="192.168.1.2",
                    command_sequences={
                        "shared_seq": ["cmd6"],  # Same name as device1
                    },
                ),
            }
        )

        sequences = config.get_all_sequences()
        assert "device_seq" in sequences
        assert sequences["device_seq"]["origin"] == "device"
        assert sequences["device_seq"]["commands"] == ["cmd3", "cmd4"]
        assert sequences["device_seq"]["sources"] == ["device1"]

        # shared_seq should track multiple sources
        assert "shared_seq" in sequences
        assert sequences["shared_seq"]["origin"] == "device"
        assert set(sequences["shared_seq"]["sources"]) == {"device1", "device2"}

    def test_get_all_sequences_global_precedence(self) -> None:
        """Test that global sequences take precedence over device sequences."""
        config = NetworkConfig(
            global_command_sequences={
                "shared_seq": CommandSequence(
                    description="Global version",
                    commands=["global_cmd"],
                )
            },
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1",
                    command_sequences={
                        "shared_seq": ["device_cmd"],  # Should be overridden
                    },
                )
            },
        )

        sequences = config.get_all_sequences()
        assert "shared_seq" in sequences
        assert sequences["shared_seq"]["origin"] == "global"
        assert sequences["shared_seq"]["commands"] == ["global_cmd"]
        assert sequences["shared_seq"]["sources"] == ["global"]

    def test_get_all_sequences_empty_config(self) -> None:
        """Test get_all_sequences with empty config."""
        config = NetworkConfig()
        sequences = config.get_all_sequences()
        assert sequences == {}

    def test_resolve_sequence_commands_global(self) -> None:
        """Test resolve_sequence_commands with global sequence."""
        config = NetworkConfig(
            global_command_sequences={
                "test_seq": CommandSequence(
                    description="Test sequence",
                    commands=["cmd1", "cmd2"],
                )
            }
        )

        commands = config.resolve_sequence_commands("test_seq")
        assert commands == ["cmd1", "cmd2"]

    def test_resolve_sequence_commands_vendor(self) -> None:
        """Test resolve_sequence_commands with vendor sequence."""
        config = NetworkConfig(
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                )
            },
            vendor_sequences={
                "mikrotik_routeros": {
                    "vendor_seq": VendorSequence(
                        description="Vendor sequence",
                        commands=["vendor_cmd1", "vendor_cmd2"],
                    )
                }
            },
        )

        commands = config.resolve_sequence_commands("vendor_seq", "test_device")
        assert commands == ["vendor_cmd1", "vendor_cmd2"]

    def test_resolve_sequence_commands_device_fallback(self) -> None:
        """Test resolve_sequence_commands falling back to device sequence."""
        config = NetworkConfig(
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1",
                    command_sequences={
                        "device_seq": ["device_cmd1", "device_cmd2"],
                    },
                ),
                "device2": DeviceConfig(
                    host="192.168.1.2",
                    # No command_sequences
                ),
            }
        )

        commands = config.resolve_sequence_commands("device_seq")
        assert commands == ["device_cmd1", "device_cmd2"]

    def test_resolve_sequence_commands_not_found(self) -> None:
        """Test resolve_sequence_commands with non-existent sequence."""
        config = NetworkConfig()
        commands = config.resolve_sequence_commands("nonexistent")
        assert commands is None

    def test_resolve_sequence_commands_vendor_fallback(self) -> None:
        """Test resolve_sequence_commands with vendor sequence fallback."""
        config = NetworkConfig(
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    command_sequences={
                        "fallback_seq": ["device_fallback_cmd"],
                    },
                )
            },
            vendor_sequences={
                "mikrotik_routeros": {
                    "vendor_seq": VendorSequence(
                        description="Vendor sequence",
                        commands=["vendor_cmd"],
                    )
                }
            },
        )

        # Should find vendor sequence
        commands = config.resolve_sequence_commands("vendor_seq", "test_device")
        assert commands == ["vendor_cmd"]

        # Should fall back to device sequence when vendor not found
        commands = config.resolve_sequence_commands("fallback_seq", "test_device")
        assert commands == ["device_fallback_cmd"]


class TestDotenvSupport:
    """Test .env file support for credentials."""

    def test_get_env_credential_from_dotenv_cwd(self, tmp_path: Path) -> None:
        """Test loading credentials from .env file in current working directory."""
        # Change to temporary directory
        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # Create .env file in current directory
            env_file = tmp_path / ".env"
            env_content = """
NT_DEFAULT_USER=dotenv_user
NT_DEFAULT_PASSWORD=dotenv_pass
NT_TESTDEVICE_USER=device_dotenv_user
NT_TESTDEVICE_PASSWORD=device_dotenv_pass
"""
            env_file.write_text(env_content.strip())

            # Clear environment variables to ensure we're testing .env loading
            old_env = {}
            for var in [
                "NT_DEFAULT_USER",
                "NT_DEFAULT_PASSWORD",
                "NT_TESTDEVICE_USER",
                "NT_TESTDEVICE_PASSWORD",
            ]:
                old_env[var] = os.environ.get(var)
                if var in os.environ:
                    del os.environ[var]

            try:
                # Load .env files
                load_dotenv_files()

                # Test default credentials
                assert get_env_credential(credential_type="user") == "dotenv_user"
                assert get_env_credential(credential_type="password") == "dotenv_pass"

                # Test device-specific credentials
                assert get_env_credential("testdevice", "user") == "device_dotenv_user"
                assert get_env_credential("testdevice", "password") == "device_dotenv_pass"

            finally:
                # Restore environment variables
                for var, value in old_env.items():
                    if value is not None:
                        os.environ[var] = value
                    elif var in os.environ:
                        del os.environ[var]
        finally:
            os.chdir(original_cwd)

    def test_get_env_credential_from_dotenv_config_dir(self, tmp_path: Path) -> None:
        """Test loading credentials from .env file in config directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create .env file in config directory
        env_file = config_dir / ".env"
        env_content = """
NT_DEFAULT_USER=config_dotenv_user
NT_DEFAULT_PASSWORD=config_dotenv_pass
"""
        env_file.write_text(env_content.strip())

        # Clear environment variables
        old_env = {}
        for var in ["NT_DEFAULT_USER", "NT_DEFAULT_PASSWORD"]:
            old_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Load .env files from config directory
            load_dotenv_files(config_dir)

            # Test credentials are loaded
            assert get_env_credential(credential_type="user") == "config_dotenv_user"
            assert get_env_credential(credential_type="password") == "config_dotenv_pass"

        finally:
            # Restore environment variables
            for var, value in old_env.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]

    def test_dotenv_precedence_config_over_cwd(self, tmp_path: Path) -> None:
        """Test that config directory .env takes precedence over cwd .env."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Change to temporary directory
        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # Create .env file in current directory (lower priority)
            cwd_env = tmp_path / ".env"
            cwd_env.write_text("NT_DEFAULT_USER=cwd_user\nNT_DEFAULT_PASSWORD=cwd_pass")

            # Create .env file in config directory (higher priority)
            config_env = config_dir / ".env"
            config_env.write_text("NT_DEFAULT_USER=config_user\nNT_DEFAULT_PASSWORD=config_pass")

            # Clear environment variables
            old_env = {}
            for var in ["NT_DEFAULT_USER", "NT_DEFAULT_PASSWORD"]:
                old_env[var] = os.environ.get(var)
                if var in os.environ:
                    del os.environ[var]

            try:
                # Load .env files
                load_dotenv_files(config_dir)

                # Config directory .env should take precedence
                assert get_env_credential(credential_type="user") == "config_user"
                assert get_env_credential(credential_type="password") == "config_pass"

            finally:
                # Restore environment variables
                for var, value in old_env.items():
                    if value is not None:
                        os.environ[var] = value
                    elif var in os.environ:
                        del os.environ[var]
        finally:
            os.chdir(original_cwd)

    def test_environment_variables_override_dotenv(self, tmp_path: Path) -> None:
        """Test that environment variables take precedence over .env files."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("NT_DEFAULT_USER=dotenv_user\nNT_DEFAULT_PASSWORD=dotenv_pass")

        # Set environment variables (should take precedence)
        os.environ["NT_DEFAULT_USER"] = "env_user"
        os.environ["NT_DEFAULT_PASSWORD"] = "env_pass"

        try:
            # Load .env files
            load_dotenv_files(tmp_path)

            # Environment variables should take precedence
            assert get_env_credential(credential_type="user") == "env_user"
            assert get_env_credential(credential_type="password") == "env_pass"

        finally:
            # Clean up environment variables
            if "NT_DEFAULT_USER" in os.environ:
                del os.environ["NT_DEFAULT_USER"]
            if "NT_DEFAULT_PASSWORD" in os.environ:
                del os.environ["NT_DEFAULT_PASSWORD"]

    def test_load_config_with_dotenv(self, tmp_path: Path) -> None:
        """Test that load_config automatically loads .env files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create .env file with credentials
        env_file = config_dir / ".env"
        env_file.write_text("NT_DEFAULT_USER=dotenv_config_user\nNT_DEFAULT_PASSWORD=dotenv_config_pass")

        # Create minimal config file
        config_file = config_dir / "config.yml"
        config_data = {
            "general": {
                "timeout": 30,
            }
        }
        config_file.write_text(yaml.safe_dump(config_data))

        # Create devices file
        devices_file = config_dir / "devices.yml"
        devices_data = {
            "devices": {
                "test_device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                }
            }
        }
        devices_file.write_text(yaml.safe_dump(devices_data))

        # Clear environment variables
        old_env = {}
        for var in ["NT_DEFAULT_USER", "NT_DEFAULT_PASSWORD"]:
            old_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Load config (should automatically load .env)
            config = load_config(config_dir)

            # Credentials should be available from .env file
            assert config.general.default_user == "dotenv_config_user"
            assert config.general.default_password == "dotenv_config_pass"

        finally:
            # Restore environment variables
            for var, value in old_env.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]

    def test_load_legacy_config_with_dotenv(self, tmp_path: Path) -> None:
        """Test that legacy config loading also loads .env files."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("NT_DEFAULT_USER=legacy_dotenv_user\nNT_DEFAULT_PASSWORD=legacy_dotenv_pass")

        # Create legacy config file
        config_file = tmp_path / "devices.yml"
        config_data = {
            "general": {
                "timeout": 30,
            },
            "devices": {
                "test_device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                }
            },
        }
        config_file.write_text(yaml.safe_dump(config_data))

        # Clear environment variables
        old_env = {}
        for var in ["NT_DEFAULT_USER", "NT_DEFAULT_PASSWORD"]:
            old_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Load legacy config (should automatically load .env)
            config = load_config(config_file)

            # Credentials should be available from .env file
            assert config.general.default_user == "legacy_dotenv_user"
            assert config.general.default_password == "legacy_dotenv_pass"

        finally:
            # Restore environment variables
            for var, value in old_env.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]

    def test_dotenv_device_specific_credentials(self, tmp_path: Path) -> None:
        """Test device-specific credentials in .env files."""
        # Create .env file with device-specific credentials
        env_file = tmp_path / ".env"
        env_content = """
NT_DEFAULT_USER=default_user
NT_DEFAULT_PASSWORD=default_pass
NT_SWITCH1_USER=switch1_user
NT_SWITCH1_PASSWORD=switch1_pass
NT_ROUTER_MAIN_USER=router_main_user
NT_ROUTER_MAIN_PASSWORD=router_main_pass
"""
        env_file.write_text(env_content.strip())

        # Clear environment variables
        old_env = {}
        env_vars = [
            "NT_DEFAULT_USER",
            "NT_DEFAULT_PASSWORD",
            "NT_SWITCH1_USER",
            "NT_SWITCH1_PASSWORD",
            "NT_ROUTER_MAIN_USER",
            "NT_ROUTER_MAIN_PASSWORD",
        ]
        for var in env_vars:
            old_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Load .env files
            load_dotenv_files(tmp_path)

            # Test default credentials
            assert get_env_credential(credential_type="user") == "default_user"
            assert get_env_credential(credential_type="password") == "default_pass"

            # Test device-specific credentials
            assert get_env_credential("switch1", "user") == "switch1_user"
            assert get_env_credential("switch1", "password") == "switch1_pass"

            # Test device with hyphen (should be converted to underscore)
            assert get_env_credential("router-main", "user") == "router_main_user"
            assert get_env_credential("router-main", "password") == "router_main_pass"

        finally:
            # Restore environment variables
            for var, value in old_env.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]

    def test_dotenv_missing_files(self, tmp_path: Path) -> None:
        """Test behavior when .env files don't exist."""
        # This should not raise an error
        load_dotenv_files(tmp_path)

        # Should return None for missing credentials
        assert get_env_credential(credential_type="user") is None
        assert get_env_credential(credential_type="password") is None

    def test_dotenv_empty_file(self, tmp_path: Path) -> None:
        """Test behavior with empty .env file."""
        # Create empty .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        # This should not raise an error
        load_dotenv_files(tmp_path)

        # Should return None for missing credentials
        assert get_env_credential(credential_type="user") is None
        assert get_env_credential(credential_type="password") is None

    def test_dotenv_malformed_file(self, tmp_path: Path) -> None:
        """Test behavior with malformed .env file."""
        # Create malformed .env file
        env_file = tmp_path / ".env"
        env_file.write_text("MALFORMED LINE WITHOUT EQUALS\nVALID_VAR=value")

        # This should not raise an error (python-dotenv is tolerant)
        load_dotenv_files(tmp_path)

        # Valid variable should still be loaded
        assert os.getenv("VALID_VAR") == "value"

        # Clean up
        if "VALID_VAR" in os.environ:
            del os.environ["VALID_VAR"]


class TestGeneralConfigDotenvIntegration:
    """Test GeneralConfig integration with .env files."""

    def test_default_user_property_with_dotenv(self, tmp_path: Path) -> None:
        """Test default_user property reads from .env file."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("NT_DEFAULT_USER=dotenv_test_user")

        # Clear environment variables
        old_user = os.environ.get("NT_DEFAULT_USER")
        if "NT_DEFAULT_USER" in os.environ:
            del os.environ["NT_DEFAULT_USER"]

        try:
            # Load .env files
            load_dotenv_files(tmp_path)

            # Create config and test property
            config = GeneralConfig()
            assert config.default_user == "dotenv_test_user"

        finally:
            # Restore environment variable
            if old_user is not None:
                os.environ["NT_DEFAULT_USER"] = old_user
            elif "NT_DEFAULT_USER" in os.environ:
                del os.environ["NT_DEFAULT_USER"]

    def test_default_password_property_with_dotenv(self, tmp_path: Path) -> None:
        """Test default_password property reads from .env file."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("NT_DEFAULT_PASSWORD=dotenv_test_pass")

        # Clear environment variables
        old_password = os.environ.get("NT_DEFAULT_PASSWORD")
        if "NT_DEFAULT_PASSWORD" in os.environ:
            del os.environ["NT_DEFAULT_PASSWORD"]

        try:
            # Load .env files
            load_dotenv_files(tmp_path)

            # Create config and test property
            config = GeneralConfig()
            assert config.default_password == "dotenv_test_pass"

        finally:
            # Restore environment variable
            if old_password is not None:
                os.environ["NT_DEFAULT_PASSWORD"] = old_password
            elif "NT_DEFAULT_PASSWORD" in os.environ:
                del os.environ["NT_DEFAULT_PASSWORD"]

    def test_dotenv_error_messages_updated(self, tmp_path: Path) -> None:
        """Test that error messages mention .env files."""
        # Clear environment variables
        old_user = os.environ.get("NT_DEFAULT_USER")
        old_password = os.environ.get("NT_DEFAULT_PASSWORD")

        if "NT_DEFAULT_USER" in os.environ:
            del os.environ["NT_DEFAULT_USER"]
        if "NT_DEFAULT_PASSWORD" in os.environ:
            del os.environ["NT_DEFAULT_PASSWORD"]

        try:
            config = GeneralConfig()

            # Test user error message mentions .env
            with pytest.raises(ValueError, match=r".*\.env.*"):
                _ = config.default_user

            # Test password error message mentions .env
            with pytest.raises(ValueError, match=r".*\.env.*"):
                _ = config.default_password

        finally:
            # Restore environment variables
            if old_user is not None:
                os.environ["NT_DEFAULT_USER"] = old_user
            if old_password is not None:
                os.environ["NT_DEFAULT_PASSWORD"] = old_password
