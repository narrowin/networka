# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Pytest configuration and fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config_data(temp_dir: Path) -> dict[str, Any]:
    """Sample configuration data for testing."""
    return {
        "general": {
            "firmware_dir": str(temp_dir / "firmware"),
            "backup_dir": str(temp_dir / "backups"),
            "logs_dir": str(temp_dir / "logs"),
            "results_dir": str(temp_dir / "results"),
            "transport": "ssh",
            "port": 22,
            "timeout": 30,
            "connection_retries": 3,
            "retry_delay": 5,
            "transfer_timeout": 300,
            "verify_checksums": True,
            "command_timeout": 60,
            "enable_logging": True,
            "log_level": "INFO",
            "backup_retention_days": 30,
            "max_backups_per_device": 10,
            "store_results": False,
            "results_format": "txt",
            "results_include_timestamp": True,
            "results_include_command": True,
        },
        "devices": {
            "test_device1": {
                "host": "192.168.1.10",
                "description": "Test Device 1",
                "device_type": "mikrotik_routeros",
                "model": "CRS328-24P-4S+",
                "platform": "mipsbe",
                "location": "Test Lab",
                "user": "admin",
                "password": "testpass",
                "tags": ["switch", "access", "lab"],
                "command_sequences": {
                    "health_check": [
                        "/system/health/print",
                        "/system/resource/print",
                    ]
                },
            },
            "test_device2": {
                "host": "192.168.1.20",
                "description": "Test Device 2",
                "user": "testuser",
                "password": "testpass2",
                "tags": ["router", "core"],
                "overrides": {
                    "timeout": 60,
                    "port": 2222,
                },
            },
            "test_device3": {
                "host": "192.168.1.30",
                "description": "Test Device 3",
                "user": "admin",
                "password": "testpass3",
                "tags": ["switch", "distribution"],
            },
        },
        "device_groups": {
            "all_switches": {
                "description": "All switch devices",
                "match_tags": ["switch"],
            },
            "lab_devices": {
                "description": "Lab devices",
                "members": ["test_device1", "test_device2"],
            },
            "core_network": {
                "description": "Core network devices",
                "members": ["test_device2"],
                "match_tags": ["core"],
            },
        },
        "global_command_sequences": {
            "system_info": {
                "description": "Get system information",
                "commands": [
                    "/system/identity/print",
                    "/system/resource/print",
                    "/system/clock/print",
                ],
            },
            "interface_status": {
                "description": "Check interface status",
                "commands": [
                    "/interface/print brief",
                    "/interface/ethernet/print brief",
                ],
            },
        },
        "file_operations": {
            "firmware_upload": {
                "local_path": str(temp_dir / "firmware" / "routeros-7.12.npk"),
                "remote_path": "/routeros-7.12.npk",
                "verify_checksum": True,
                "backup_before_upgrade": True,
            },
            "config_backup": {
                "remote_files": ["/export.rsc", "/system.backup"],
                "compress": True,
            },
        },
    }


@pytest.fixture
def sample_config(sample_config_data: dict[str, Any]) -> NetworkConfig:
    """Create a NetworkConfig instance from sample data."""
    return NetworkConfig(**sample_config_data)


@pytest.fixture
def config_file(temp_dir: Path, sample_config_data: dict[str, Any]) -> Path:
    """Create a temporary config file with sample data."""
    config_path = temp_dir / "test_config.yml"
    with config_path.open("w") as f:
        yaml.dump(sample_config_data, f)
    return config_path


@pytest.fixture
def invalid_config_file(temp_dir: Path) -> Path:
    """Create an invalid config file for testing error handling."""
    config_path = temp_dir / "invalid_config.yml"
    with config_path.open("w") as f:
        f.write("invalid: yaml: content: [")
    return config_path


@pytest.fixture
def mock_scrapli_driver() -> MagicMock:
    """Mock Scrapli driver for testing."""
    driver = MagicMock()
    driver.open = MagicMock()
    driver.close = MagicMock()

    # Create a mock response with proper attributes
    mock_response = MagicMock()
    mock_response.result = "test output"
    mock_response.failed = False

    driver.send_command = MagicMock(return_value=mock_response)
    driver.send_commands = MagicMock(return_value=[mock_response])
    driver.channel = MagicMock()
    driver.channel.send_input = MagicMock()
    driver.channel.read_until_prompt = MagicMock()
    return driver


@pytest.fixture
def mock_device_session(
    sample_config: NetworkConfig, mock_scrapli_driver: MagicMock
) -> DeviceSession:
    """Mock DeviceSession for testing."""
    session = DeviceSession("test_device1", sample_config)
    # Access protected members for testing purposes
    session._driver = mock_scrapli_driver
    session._connected = True
    return session


@pytest.fixture
def mock_command_result() -> MagicMock:
    """Mock command result for testing."""
    result = MagicMock()
    result.result = "test output"
    result.failed = False
    result.channel_log = "test log"
    return result


@pytest.fixture
def mock_failed_command_result() -> MagicMock:
    """Mock failed command result for testing."""
    result = MagicMock()
    result.result = "error output"
    result.failed = True
    result.channel_log = "error log"
    return result


@pytest.fixture
def firmware_file(temp_dir: Path) -> Path:
    """Create a mock firmware file."""
    firmware_path = temp_dir / "test_firmware.npk"
    firmware_path.write_bytes(b"mock firmware content")
    return firmware_path


@pytest.fixture
def backup_file(temp_dir: Path) -> Path:
    """Create a mock backup file."""
    backup_path = temp_dir / "test_backup.backup"
    backup_path.write_bytes(b"mock backup content")
    return backup_path


@pytest.fixture
def mock_paramiko_sftp() -> MagicMock:
    """Mock paramiko SFTP client."""
    sftp = MagicMock()
    sftp.put = MagicMock()
    sftp.get = MagicMock()
    sftp.stat = MagicMock()
    sftp.close = MagicMock()
    return sftp


@pytest.fixture
def mock_paramiko_ssh() -> MagicMock:
    """Mock paramiko SSH client."""
    ssh = MagicMock()
    ssh.connect = MagicMock()
    ssh.open_sftp = MagicMock()
    ssh.close = MagicMock()
    return ssh
