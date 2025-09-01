# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for configuration management."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from network_toolkit.config import (
    DeviceConfig,
    DeviceGroup,
    DeviceOverrides,
    FileOperationConfig,
    GeneralConfig,
    GroupCredentials,
    NetworkConfig,
    VendorPlatformConfig,
    VendorSequence,
    load_config,
    load_dotenv_files,
)
from network_toolkit.credentials import EnvironmentCredentialManager
from network_toolkit.exceptions import NetworkToolkitError


class TestGeneralConfig:
    """Test GeneralConfig model validation."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        # Set up environment variables for testing
        os.environ["NW_USER_DEFAULT"] = "admin"
        os.environ["NW_PASSWORD_DEFAULT"] = "admin"

        try:
            config = GeneralConfig()
            assert config.firmware_dir == "/tmp/firmware"
            assert config.backup_dir == "/tmp/backups"
            assert config.default_user == "admin"
            assert config.default_password == "admin"
            assert config.transport == "system"
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
        finally:
            # Clean up environment variables
            if "NW_USER_DEFAULT" in os.environ:
                del os.environ["NW_USER_DEFAULT"]
            if "NW_PASSWORD_DEFAULT" in os.environ:
                del os.environ["NW_PASSWORD_DEFAULT"]

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
        for transport in ["system", "telnet", "paramiko", "ssh2"]:
            config = GeneralConfig(transport=transport)
            assert config.transport == transport.lower()

        # Invalid transport
        with pytest.raises(Exception, match="transport must be one of"):
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
        group = DeviceGroup(
            description="Test group", members=["device1"], match_tags=["switch"]
        )
        assert group.description == "Test group"
        assert group.members == ["device1"]
        assert group.match_tags == ["switch"]


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
        assert config.file_operations is None

    def test_get_device_connection_params_nonexistent_device(self) -> None:
        """Test getting connection params for nonexistent device."""
        config = NetworkConfig()
        with pytest.raises(ValueError, match="Device 'nonexistent' not found"):
            config.get_device_connection_params("nonexistent")

    def test_get_device_connection_params_basic(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test getting basic device connection parameters."""
        params = sample_config.get_device_connection_params("test_device1")

        expected = {
            "host": "192.168.1.10",
            "auth_username": "admin",
            "auth_password": "testpass",
            "port": 22,
            "timeout_socket": 30,
            "timeout_transport": 30,
            "transport": "system",
            "platform": "mikrotik_routeros",  # Now correctly uses device_type, not hardware platform
        }

        assert params == expected

    def test_get_device_connection_params_with_overrides(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test getting device connection parameters with overrides."""
        params = sample_config.get_device_connection_params("test_device2")

        expected = {
            "host": "192.168.1.20",
            "auth_username": "testuser",
            "auth_password": "testpass2",
            "port": 2222,
            "timeout_socket": 60,
            "timeout_transport": 60,
            "transport": "system",
            "platform": "mikrotik_routeros",
        }

        assert params == expected

    def test_get_group_members_nonexistent_group(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test getting members of nonexistent group."""
        with pytest.raises(NetworkToolkitError, match="Device group 'nonexistent'"):
            sample_config.get_group_members("nonexistent")

    def test_get_group_members_direct_members(
        self, sample_config: NetworkConfig
    ) -> None:
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
        assert config.transport == "system"
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
        with pytest.raises(
            ValueError,
            match="transport must be one of: system, paramiko, ssh2, telnet, asyncssh, asynctelnet",
        ):
            GeneralConfig(transport="invalid")

    def test_general_config_valid_transports(self) -> None:
        """Test general config with valid transports."""
        valid_transports = [
            "system",
            "paramiko",
            "ssh2",
            "telnet",
            "asyncssh",
            "asynctelnet",
        ]
        for transport in valid_transports:
            config = GeneralConfig(transport=transport)
            assert config.transport == transport.lower()

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
        old_user = os.environ.get("NW_USER_DEFAULT")
        old_pass = os.environ.get("NW_PASSWORD_DEFAULT")

        if "NW_USER_DEFAULT" in os.environ:
            del os.environ["NW_USER_DEFAULT"]
        if "NW_PASSWORD_DEFAULT" in os.environ:
            del os.environ["NW_PASSWORD_DEFAULT"]

        # Temporarily move .env file to avoid auto-loading
        env_file = Path.cwd() / ".env"
        env_backup = None
        if env_file.exists():
            env_backup = Path.cwd() / ".env.backup"
            env_file.rename(env_backup)

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
            # Restore .env file
            if env_backup and env_backup.exists():
                env_backup.rename(env_file)

            # Restore environment variables
            if old_user is not None:
                os.environ["NW_USER_DEFAULT"] = old_user
            if old_pass is not None:
                os.environ["NW_PASSWORD_DEFAULT"] = old_pass

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

    def test_network_config_environment_variable_substitution(
        self, tmp_path: Path
    ) -> None:
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
        fragment_file.write_text(
            "devices:\n  test:\n    host: 192.168.1.1\n    invalid: ["
        )

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

    # Legacy single-file YAML mode removed; no legacy config tests remain


class TestGroupCredentials:
    """Test group credential functionality."""

    def test_group_credentials_creation(self) -> None:
        """Test GroupCredentials model creation."""
        # Empty credentials
        creds = GroupCredentials()
        assert creds.user is None
        assert creds.password is None

        # With user only
        creds = GroupCredentials(user="admin")
        assert creds.user == "admin"
        assert creds.password is None

        # With password only
        creds = GroupCredentials(password="secret")
        assert creds.user is None
        assert creds.password == "secret"

        # With both
        creds = GroupCredentials(user="admin", password="secret")
        assert creds.user == "admin"
        assert creds.password == "secret"

    def test_device_group_with_credentials(self) -> None:
        """Test DeviceGroup with credentials."""
        # Group without credentials
        group = DeviceGroup(description="Test group", members=["device1"])
        assert group.credentials is None

        # Group with credentials
        creds = GroupCredentials(
            user="group_admin", password="group_pass"
        )  # pragma: allowlist secret
        group = DeviceGroup(
            description="Test group with creds",
            members=["device1"],
            credentials=creds,
        )
        assert group.credentials is not None
        assert group.credentials.user == "group_admin"
        assert group.credentials.password == "group_pass"  # pragma: allowlist secret

    def test_get_device_groups(self) -> None:
        """Test getting groups that a device belongs to."""
        config_data = {
            "general": {},
            "devices": {
                "device1": {"host": "192.168.1.1", "tags": ["switch", "production"]},
                "device2": {"host": "192.168.1.2", "tags": ["router"]},
            },
            "device_groups": {
                "switches": {"description": "All switches", "members": ["device1"]},
                "production": {
                    "description": "Production devices",
                    "match_tags": ["production"],
                },
                "routers": {"description": "All routers", "match_tags": ["router"]},
            },
        }

        config = NetworkConfig(**config_data)

        # Device1 should be in both 'switches' (explicit) and 'production' (tag-based)
        groups = config.get_device_groups("device1")
        assert set(groups) == {"switches", "production"}

        # Device2 should only be in 'routers' (tag-based)
        groups = config.get_device_groups("device2")
        assert groups == ["routers"]

        # Non-existent device should return empty list
        groups = config.get_device_groups("nonexistent")
        assert groups == []

    def test_get_group_credentials_config_only(self) -> None:
        """Test getting group credentials from config only."""
        config_data = {
            "general": {},
            "devices": {"device1": {"host": "192.168.1.1", "tags": ["production"]}},
            "device_groups": {
                "production": {
                    "description": "Production devices",
                    "match_tags": ["production"],
                    "credentials": {
                        "user": "prod_admin",
                        "password": "prod_pass",
                    },  # pragma: allowlist secret
                },
                "staging": {
                    "description": "Staging devices",
                    "match_tags": ["staging"],
                    "credentials": {"user": "stage_admin"},  # No password in config
                },
            },
        }

        config = NetworkConfig(**config_data)

        # Should get credentials from production group
        user, password = config.get_group_credentials("device1")
        assert user == "prod_admin"
        assert password == "prod_pass"  # pragma: allowlist secret

    def test_get_group_credentials_env_vars(self) -> None:
        """Test getting group credentials from environment variables."""
        # Set up test environment variables
        os.environ["NW_USER_PRODUCTION"] = "env_prod_user"
        os.environ["NW_PASSWORD_PRODUCTION"] = (
            "env_prod_pass"  # pragma: allowlist secret
        )

        try:
            config_data = {
                "general": {},
                "devices": {"device1": {"host": "192.168.1.1", "tags": ["production"]}},
                "device_groups": {
                    "production": {
                        "description": "Production devices",
                        "match_tags": ["production"],
                        "credentials": {},  # Empty credentials in config
                    }
                },
            }

            config = NetworkConfig(**config_data)

            # Should get credentials from environment variables
            user, password = config.get_group_credentials("device1")
            assert user == "env_prod_user"
            assert password == "env_prod_pass"  # pragma: allowlist secret

        finally:
            # Clean up environment variables
            if "NW_USER_PRODUCTION" in os.environ:
                del os.environ["NW_USER_PRODUCTION"]
            if "NW_PASSWORD_PRODUCTION" in os.environ:
                del os.environ["NW_PASSWORD_PRODUCTION"]

    def test_get_group_credentials_no_groups(self) -> None:
        """Test getting group credentials when device has no groups."""
        config_data = {
            "general": {},
            "devices": {"device1": {"host": "192.168.1.1"}},  # No tags
            "device_groups": {
                "production": {
                    "description": "Production devices",
                    "match_tags": ["production"],
                    "credentials": {
                        "user": "prod_admin",
                        "password": "prod_pass",
                    },  # pragma: allowlist secret
                }
            },
        }

        config = NetworkConfig(**config_data)

        # Should return None for both since device doesn't belong to any groups
        user, password = config.get_group_credentials("device1")
        assert user is None
        assert password is None

    def test_get_device_connection_params_with_group_credentials(self) -> None:
        """Test connection params resolution with group credentials."""
        # Set up environment for defaults
        os.environ["NW_USER_DEFAULT"] = "default_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "default_pass"  # pragma: allowlist secret

        try:
            config_data = {
                "general": {},
                "devices": {
                    "device1": {"host": "192.168.1.1", "tags": ["production"]},
                    # No explicit credentials
                    "device2": {
                        "host": "192.168.1.2",
                        "user": "device_user",
                        "password": "device_pass",  # pragma: allowlist secret
                        "tags": ["production"],
                    },
                    # Has explicit credentials - should take precedence
                    "device3": {"host": "192.168.1.3"},  # No tags, use defaults
                },
                "device_groups": {
                    "production": {
                        "description": "Production devices",
                        "match_tags": ["production"],
                        "credentials": {"user": "prod_user", "password": "prod_pass"},
                    }
                },
            }

            config = NetworkConfig(**config_data)

            # Device1: Should use group credentials
            params = config.get_device_connection_params("device1")
            assert params["auth_username"] == "prod_user"
            assert params["auth_password"] == "prod_pass"

            # Device2: Device credentials should take precedence over group
            params = config.get_device_connection_params("device2")
            assert params["auth_username"] == "device_user"
            assert params["auth_password"] == "device_pass"  # pragma: allowlist secret

            # Device3: Should fall back to defaults
            params = config.get_device_connection_params("device3")
            assert params["auth_username"] == "default_user"
            assert params["auth_password"] == "default_pass"  # pragma: allowlist secret

        finally:
            # Clean up environment variables
            if "NW_USER_DEFAULT" in os.environ:
                del os.environ["NW_USER_DEFAULT"]
            if "NW_PASSWORD_DEFAULT" in os.environ:
                del os.environ["NW_PASSWORD_DEFAULT"]

    def test_credential_precedence_order(self) -> None:
        """Test the complete credential precedence order."""
        # Set up all credential sources
        os.environ["NW_USER_DEFAULT"] = "default_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "default_pass"  # pragma: allowlist secret
        os.environ["NW_USER_DEVICE1"] = "env_device_user"
        os.environ["NW_PASSWORD_DEVICE1"] = (
            "env_device_pass"  # pragma: allowlist secret
        )

        try:
            config_data = {
                "general": {},
                "devices": {
                    "device1": {
                        "host": "192.168.1.1",
                        "user": "config_device_user",
                        "password": "config_device_pass",  # pragma: allowlist secret
                        "tags": ["production"],
                    }
                },
                "device_groups": {
                    "production": {
                        "description": "Production devices",
                        "match_tags": ["production"],
                        "credentials": {
                            "user": "group_user",
                            "password": "group_pass",
                        },  # pragma: allowlist secret
                    }
                },
            }

            config = NetworkConfig(**config_data)

            # Test precedence: device config > device env vars > group > defaults
            params = config.get_device_connection_params("device1")
            # Device config should win
            assert params["auth_username"] == "config_device_user"
            assert (
                params["auth_password"] == "config_device_pass"
            )  # pragma: allowlist secret

            # Test with interactive override (highest precedence)
            params = config.get_device_connection_params(
                "device1",
                username_override="interactive_user",
                password_override="interactive_pass",  # pragma: allowlist secret
            )
            assert params["auth_username"] == "interactive_user"
            assert (
                params["auth_password"] == "interactive_pass"
            )  # pragma: allowlist secret

        finally:
            # Clean up environment variables
            for key in [
                "NW_USER_DEFAULT",
                "NW_PASSWORD_DEFAULT",
                "NW_USER_DEVICE1",
                "NW_PASSWORD_DEVICE1",
            ]:
                if key in os.environ:
                    del os.environ[key]


class TestEnvironmentCredentialManager:
    """Test the EnvironmentCredentialManager class with new NW_ prefix."""

    def test_get_device_specific(self) -> None:
        """Test getting device-specific credentials."""
        os.environ["NW_USER_TESTDEV"] = "device_user"
        os.environ["NW_PASSWORD_TESTDEV"] = "device_pass"  # pragma: allowlist secret

        try:
            # Test device-specific user
            result = EnvironmentCredentialManager.get_device_specific("testdev", "user")
            assert result == "device_user"

            # Test device-specific password
            result = EnvironmentCredentialManager.get_device_specific(
                "testdev", "password"
            )
            assert result == "device_pass"

            # Test case insensitive device name (should convert to uppercase)
            result = EnvironmentCredentialManager.get_device_specific("TestDev", "user")
            assert result == "device_user"

        finally:
            if "NW_USER_TESTDEV" in os.environ:
                del os.environ["NW_USER_TESTDEV"]
            if "NW_PASSWORD_TESTDEV" in os.environ:
                del os.environ["NW_PASSWORD_TESTDEV"]

    def test_get_group_specific(self) -> None:
        """Test getting group-specific credentials."""
        os.environ["NW_USER_PRODUCTION"] = "group_user"
        os.environ["NW_PASSWORD_PRODUCTION"] = "group_pass"  # pragma: allowlist secret

        try:
            # Test group-specific user
            result = EnvironmentCredentialManager.get_group_specific(
                "production", "user"
            )
            assert result == "group_user"

            # Test group-specific password
            result = EnvironmentCredentialManager.get_group_specific(
                "production", "password"
            )
            assert result == "group_pass"

        finally:
            if "NW_USER_PRODUCTION" in os.environ:
                del os.environ["NW_USER_PRODUCTION"]
            if "NW_PASSWORD_PRODUCTION" in os.environ:
                del os.environ["NW_PASSWORD_PRODUCTION"]

    def test_get_env_credential_defaults(self) -> None:
        """Test getting default credentials."""
        os.environ["NW_USER_DEFAULT"] = "default_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "default_pass"  # pragma: allowlist secret

        try:
            # Test default user
            result = EnvironmentCredentialManager.get_default("user")
            assert result == "default_user"

            # Test default password
            result = EnvironmentCredentialManager.get_default("password")
            assert result == "default_pass"

        finally:
            if "NW_USER_DEFAULT" in os.environ:
                del os.environ["NW_USER_DEFAULT"]
            if "NW_PASSWORD_DEFAULT" in os.environ:
                del os.environ["NW_PASSWORD_DEFAULT"]

    def test_get_env_credential_fallback(self) -> None:
        """Test fallback from specific to default credentials."""
        os.environ["NW_USER_DEFAULT"] = "default_user"
        # No device-specific credential set

        try:
            # Should fall back to default when device-specific not found
            result = EnvironmentCredentialManager.get_credential("nonexistent", "user")
            assert result == "default_user"

            # Should return None when nothing is found
            result = EnvironmentCredentialManager.get_credential(
                "nonexistent", "password"
            )
            assert result is None

        finally:
            if "NW_USER_DEFAULT" in os.environ:
                del os.environ["NW_USER_DEFAULT"]

    def test_get_env_credential_hyphen_conversion(self) -> None:
        """Test that hyphens in device names are converted to underscores."""
        os.environ["NW_USER_TEST_DEVICE"] = "test_user"

        try:
            # Device name with hyphens should be converted to underscores
            result = EnvironmentCredentialManager.get_credential("test-device", "user")
            assert result == "test_user"

        finally:
            if "NW_USER_TEST_DEVICE" in os.environ:
                del os.environ["NW_USER_TEST_DEVICE"]


class TestDotenvSupportNW:
    """Tests for .env support using NW_* variables and EnvironmentCredentialManager."""

    def test_dotenv_from_cwd(self, tmp_path: Path) -> None:
        """Credentials from .env in current working directory are loaded."""
        original_cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            env_file = tmp_path / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "NW_USER_DEFAULT=dotenv_user",
                        "NW_PASSWORD_DEFAULT=dotenv_pass",
                        "NW_USER_TESTDEVICE=device_user",
                        "NW_PASSWORD_TESTDEVICE=device_pass",
                    ]
                )
            )

            # Clear any pre-existing values to assert .env load
            for var in [
                "NW_USER_DEFAULT",
                "NW_PASSWORD_DEFAULT",
                "NW_USER_TESTDEVICE",
                "NW_PASSWORD_TESTDEVICE",
            ]:
                if var in os.environ:
                    del os.environ[var]

            load_dotenv_files()

            assert EnvironmentCredentialManager.get_default("user") == "dotenv_user"
            assert EnvironmentCredentialManager.get_default("password") == "dotenv_pass"
            assert (
                EnvironmentCredentialManager.get_device_specific("testdevice", "user")
                == "device_user"
            )
            assert (
                EnvironmentCredentialManager.get_device_specific(
                    "testdevice", "password"
                )
                == "device_pass"
            )
        finally:
            os.chdir(original_cwd)

    def test_config_dir_dotenv_precedence_over_cwd(self, tmp_path: Path) -> None:
        """.env in config dir takes precedence over cwd .env."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        original_cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            (tmp_path / ".env").write_text(
                "NW_USER_DEFAULT=cwd_user\nNW_PASSWORD_DEFAULT=cwd_pass"  # pragma: allowlist secret
            )
            (config_dir / ".env").write_text(
                "NW_USER_DEFAULT=config_user\nNW_PASSWORD_DEFAULT=config_pass"  # pragma: allowlist secret
            )

            # Clear env
            for var in ["NW_USER_DEFAULT", "NW_PASSWORD_DEFAULT"]:
                if var in os.environ:
                    del os.environ[var]

            load_dotenv_files(config_dir)

            assert EnvironmentCredentialManager.get_default("user") == "config_user"
            assert EnvironmentCredentialManager.get_default("password") == "config_pass"
        finally:
            os.chdir(original_cwd)

    def test_environment_variables_override_dotenv(self, tmp_path: Path) -> None:
        """Explicit environment variables override values from .env files."""
        (tmp_path / ".env").write_text(
            "NW_USER_DEFAULT=dotenv_user\nNW_PASSWORD_DEFAULT=dotenv_pass"  # pragma: allowlist secret
        )

        os.environ["NW_USER_DEFAULT"] = "env_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "env_pass"  # pragma: allowlist secret
        try:
            load_dotenv_files(tmp_path)
            assert EnvironmentCredentialManager.get_default("user") == "env_user"
            assert EnvironmentCredentialManager.get_default("password") == "env_pass"
        finally:
            if "NW_USER_DEFAULT" in os.environ:
                del os.environ["NW_USER_DEFAULT"]
            if "NW_PASSWORD_DEFAULT" in os.environ:
                del os.environ["NW_PASSWORD_DEFAULT"]

    def test_device_specific_hyphen_conversion_in_dotenv(self, tmp_path: Path) -> None:
        """Device names with hyphens map to underscores in NW_* variables."""
        (tmp_path / ".env").write_text(
            "NW_USER_ROUTER_MAIN=router_user\nNW_PASSWORD_ROUTER_MAIN=router_pass"
        )
        # Clear env
        for var in ["NW_USER_ROUTER_MAIN", "NW_PASSWORD_ROUTER_MAIN"]:
            if var in os.environ:
                del os.environ[var]
        load_dotenv_files(tmp_path)
        assert (
            EnvironmentCredentialManager.get_device_specific("router-main", "user")
            == "router_user"
        )
        assert (
            EnvironmentCredentialManager.get_device_specific("router-main", "password")
            == "router_pass"
        )


class TestGeneralConfigDotenvIntegrationNW:
    """GeneralConfig integration tests with NW_* dotenv support."""

    def test_default_user_and_password_from_dotenv(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        (config_dir / ".env").write_text(
            "NW_USER_DEFAULT=conf_user\nNW_PASSWORD_DEFAULT=conf_pass"  # pragma: allowlist secret
        )

        # Minimal valid config files
        (config_dir / "config.yml").write_text(
            yaml.safe_dump({"general": {"timeout": 30}})
        )
        (config_dir / "devices.yml").write_text(
            yaml.safe_dump({"devices": {"dev": {"host": "192.168.1.1"}}})
        )

        # Clear env to ensure .env is the source
        for var in ["NW_USER_DEFAULT", "NW_PASSWORD_DEFAULT"]:
            if var in os.environ:
                del os.environ[var]

        config = load_config(config_dir)
        assert config.general.default_user == "conf_user"
        assert (
            config.general.default_password == "conf_pass"
        )  # pragma: allowlist secret
