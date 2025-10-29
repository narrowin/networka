"""Tests for Cisco platform operations."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from network_toolkit.exceptions import DeviceConnectionError
from network_toolkit.platforms.base import BackupResult, UnsupportedOperationError
from network_toolkit.platforms.cisco_ios.operations import CiscoIOSOperations
from network_toolkit.platforms.cisco_iosxe.operations import CiscoIOSXEOperations


class TestCiscoIOSOperations:
    """Test Cisco IOS platform operations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.device_name = "test_switch"
        self.mock_session._connected = False  # Expect disconnected for tests
        self.platform_ops = CiscoIOSOperations(self.mock_session)

    def test_platform_metadata(self) -> None:
        """Test platform metadata methods."""
        assert self.platform_ops.get_platform_name() == "Cisco IOS"
        assert self.platform_ops.get_device_types() == [
            "cisco_ios"
        ]  # Fixed to only include cisco_ios
        supported_exts = self.platform_ops.get_supported_file_extensions()
        assert ".bin" in supported_exts
        assert ".tar" in supported_exts

    def test_firmware_upgrade_disconnected_device(self) -> None:
        """Test that firmware upgrade fails when device is disconnected."""
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix.lower.return_value = ".bin"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True

        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Device not connected" in str(exc_info.value)

    def test_firmware_downgrade_disconnected_device(self) -> None:
        """Test that firmware downgrade fails when device is disconnected."""
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix.lower.return_value = ".bin"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True

        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.firmware_downgrade(mock_firmware_path)

        assert "Device not connected" in str(exc_info.value)

    def test_bios_upgrade_not_implemented(self) -> None:
        """Test that BIOS upgrade raises UnsupportedOperationError."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.bios_upgrade()

        assert "bios_upgrade" in str(exc_info.value)
        assert "Cisco IOS" in str(exc_info.value)

    def test_create_backup_success(self) -> None:
        """Test that backup creation works successfully."""
        # Mock device session
        self.mock_session.is_connected = True
        # Mock execute_command to return success for both backup command and file checks
        self.mock_session.execute_command.return_value = "config output"

        result = self.platform_ops.create_backup(["show running-config"])

        assert isinstance(result, BackupResult)
        assert result.success is True
        assert len(result.text_outputs) > 0
        # Verify the backup command was called (it will be called along with file checks)
        assert any(
            call[0][0] == "show running-config"
            for call in self.mock_session.execute_command.call_args_list
        )

    def test_operation_support_checking(self) -> None:
        """Test that operations are reported as supported."""
        # Since these are now actual implementations, they should be supported
        assert self.platform_ops.is_operation_supported("firmware_upgrade") is True
        assert self.platform_ops.is_operation_supported("firmware_downgrade") is True
        assert self.platform_ops.is_operation_supported("bios_upgrade") is True
        assert self.platform_ops.is_operation_supported("create_backup") is True
        assert (
            self.platform_ops.is_operation_supported("nonexistent_operation") is False
        )


class TestCiscoIOSXEOperations:
    """Test Cisco IOS-XE platform operations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.device_name = "test_switch"
        self.mock_session._connected = False  # Expect disconnected for tests
        self.platform_ops = CiscoIOSXEOperations(self.mock_session)

    def test_platform_metadata(self) -> None:
        """Test platform metadata methods."""
        assert self.platform_ops.get_platform_name() == "Cisco IOS-XE"
        assert self.platform_ops.get_device_types() == ["cisco_iosxe"]
        supported_exts = self.platform_ops.get_supported_file_extensions()
        assert ".bin" in supported_exts
        assert ".pkg" in supported_exts

    def test_firmware_upgrade_disconnected_device(self) -> None:
        """Test that firmware upgrade fails when device is disconnected."""
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix.lower.return_value = ".bin"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True

        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Device not connected" in str(exc_info.value)

    def test_firmware_downgrade_disconnected_device(self) -> None:
        """Test that firmware downgrade fails when device is disconnected."""
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix.lower.return_value = ".bin"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True

        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.firmware_downgrade(mock_firmware_path)

        assert "Device not connected" in str(exc_info.value)

    def test_bios_upgrade_not_implemented(self) -> None:
        """Test that BIOS upgrade raises UnsupportedOperationError."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.bios_upgrade()

        assert "bios_upgrade" in str(exc_info.value)
        assert "Cisco IOS-XE" in str(exc_info.value)

    def test_create_backup_success(self) -> None:
        """Test that backup creation works successfully."""
        # Mock device session
        self.mock_session.is_connected = True
        # Mock execute_command to return success for both backup command and file checks
        self.mock_session.execute_command.return_value = "config output"

        result = self.platform_ops.create_backup(["show running-config"])

        assert isinstance(result, BackupResult)
        assert result.success is True
        assert len(result.text_outputs) > 0
        # Verify the backup command was called (it will be called along with file checks)
        assert any(
            call[0][0] == "show running-config"
            for call in self.mock_session.execute_command.call_args_list
        )

    def test_operation_support_checking(self) -> None:
        """Test that operations are reported as supported."""
        # Since these are now actual implementations, they should be supported
        assert self.platform_ops.is_operation_supported("firmware_upgrade") is True
        assert self.platform_ops.is_operation_supported("firmware_downgrade") is True
        assert self.platform_ops.is_operation_supported("bios_upgrade") is True
        assert self.platform_ops.is_operation_supported("create_backup") is True
        assert (
            self.platform_ops.is_operation_supported("nonexistent_operation") is False
        )
