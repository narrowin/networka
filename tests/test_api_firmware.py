"""Tests for firmware API."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.api.firmware import (
    FirmwareUpgradeOptions,
    upgrade_firmware,
)
from network_toolkit.config import NetworkConfig
from network_toolkit.exceptions import NetworkToolkitError


@pytest.fixture
def mock_config():
    config = MagicMock(spec=NetworkConfig)
    config.devices = {
        "dev1": MagicMock(device_type="cisco_ios", command_sequences={}),
        "dev2": MagicMock(device_type="mikrotik_routeros", command_sequences={}),
    }
    config.device_groups = {
        "group1": MagicMock(members=["dev1", "dev2"]),
    }
    config.get_group_members.return_value = ["dev1", "dev2"]
    config.get_transport_type.return_value = "ssh"
    return config


@patch("network_toolkit.api.firmware.check_operation_support")
@patch("network_toolkit.api.firmware.get_platform_file_extensions")
@patch("network_toolkit.api.firmware.DeviceSession")
def test_upgrade_firmware_device_success(
    mock_session_cls, mock_get_exts, mock_check_support, mock_config, tmp_path
):
    firmware_file = tmp_path / "firmware.bin"
    firmware_file.touch()

    mock_check_support.return_value = (True, None)
    mock_get_exts.return_value = [".bin"]

    mock_platform_ops = MagicMock()
    mock_platform_ops.firmware_upgrade.return_value = True
    mock_platform_ops.get_platform_name.return_value = "Cisco IOS"

    # Mock get_platform_operations to return our mock ops
    with patch("network_toolkit.api.firmware.get_platform_operations", return_value=mock_platform_ops):
        options = FirmwareUpgradeOptions(
            target="dev1",
            firmware_file=firmware_file,
            config=mock_config,
        )

        result = upgrade_firmware(options)

        assert result.success_count == 1
        assert result.failed_count == 0
        assert len(result.results) == 1
        assert result.results[0].success is True
        assert result.results[0].device_name == "dev1"
        assert result.results[0].platform == "Cisco IOS"


@patch("network_toolkit.api.firmware.check_operation_support")
def test_upgrade_firmware_not_supported(mock_check_support, mock_config, tmp_path):
    firmware_file = tmp_path / "firmware.bin"
    firmware_file.touch()

    mock_check_support.return_value = (False, "Not supported")

    options = FirmwareUpgradeOptions(
        target="dev1",
        firmware_file=firmware_file,
        config=mock_config,
    )

    result = upgrade_firmware(options)

    assert result.success_count == 0
    assert result.failed_count == 1
    assert result.results[0].success is False
    assert "Not supported" in result.results[0].message


def test_upgrade_firmware_file_not_found(mock_config):
    options = FirmwareUpgradeOptions(
        target="dev1",
        firmware_file=Path("nonexistent.bin"),
        config=mock_config,
    )

    with pytest.raises(NetworkToolkitError, match="Firmware file not found"):
        upgrade_firmware(options)
