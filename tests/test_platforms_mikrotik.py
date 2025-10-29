"""Tests for MikroTik RouterOS platform operations."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
from network_toolkit.platforms.base import BackupResult
from network_toolkit.platforms.mikrotik_routeros.operations import (
    MikroTikRouterOSOperations,
)


class TestMikroTikRouterOSOperations:
    """Test MikroTik RouterOS platform operations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.device_name = "test_router"
        self.mock_session._connected = True
        self.mock_session._transport = MagicMock()

        self.platform_ops = MikroTikRouterOSOperations(self.mock_session)

    def test_platform_metadata(self) -> None:
        """Test platform metadata methods."""
        assert self.platform_ops.get_platform_name() == "MikroTik RouterOS"
        assert self.platform_ops.get_device_types() == ["mikrotik_routeros"]
        assert self.platform_ops.get_supported_file_extensions() == [".npk"]

    def test_firmware_upgrade_success(self) -> None:
        """Test successful firmware upgrade."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True
        mock_firmware_path.name = "firmware.npk"

        # Mock successful upload
        self.mock_session.upload_file.return_value = True
        self.mock_session.execute_command.return_value = "package list output"

        # Mock successful reboot
        self.mock_session._transport.send_interactive.return_value = "reboot response"

        # Test firmware upgrade
        result = self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert result is True
        self.mock_session.upload_file.assert_called_once()
        self.mock_session._transport.send_interactive.assert_called_once()
        assert self.mock_session._connected is False  # Should disconnect after reboot

    def test_firmware_upgrade_invalid_extension(self) -> None:
        """Test firmware upgrade with invalid file extension."""
        # Mock file with wrong extension
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".bin"  # Wrong extension for RouterOS

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Invalid firmware file for RouterOS" in str(exc_info.value)
        assert ".npk" in str(exc_info.value)

    def test_firmware_upgrade_file_not_found(self) -> None:
        """Test firmware upgrade with missing file."""
        # Mock non-existent file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = False

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Firmware file not found" in str(exc_info.value)

    def test_firmware_upgrade_not_connected(self) -> None:
        """Test firmware upgrade when device not connected."""
        self.mock_session._connected = False
        mock_firmware_path = MagicMock(spec=Path)

        # Should raise DeviceConnectionError
        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Device not connected" in str(exc_info.value)

    def test_firmware_upgrade_upload_failed(self) -> None:
        """Test firmware upgrade when upload fails."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True

        # Mock failed upload
        self.mock_session.upload_file.return_value = False

        # Should raise DeviceExecutionError
        with pytest.raises(DeviceExecutionError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Firmware file upload failed" in str(exc_info.value)

    def test_firmware_downgrade_success(self) -> None:
        """Test successful firmware downgrade."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True
        mock_firmware_path.name = "firmware.npk"

        # Mock successful upload
        self.mock_session.upload_file.return_value = True
        self.mock_session.execute_command.return_value = "package list output"

        # Mock successful downgrade
        self.mock_session._transport.send_interactive.return_value = (
            "downgrade response"
        )

        # Test firmware downgrade
        result = self.platform_ops.firmware_downgrade(mock_firmware_path)

        assert result is True
        self.mock_session.upload_file.assert_called_once()
        self.mock_session._transport.send_interactive.assert_called_once()
        assert self.mock_session._connected is False  # Should disconnect after reboot

    def test_bios_upgrade_success(self) -> None:
        """Test successful BIOS/RouterBOARD upgrade."""
        # Mock successful routerboard status check
        self.mock_session.execute_command.return_value = "routerboard status"

        # Mock successful upgrade and reboot
        self.mock_session._transport.send_interactive.side_effect = [
            "upgrade response",  # RouterBOARD upgrade
            "reboot response",  # Reboot
        ]

        # Test BIOS upgrade
        result = self.platform_ops.bios_upgrade()

        assert result is True
        assert self.mock_session._transport.send_interactive.call_count == 2
        assert self.mock_session._connected is False  # Should disconnect after reboot

    def test_bios_upgrade_not_connected(self) -> None:
        """Test BIOS upgrade when device not connected."""
        self.mock_session._connected = False

        # Should raise DeviceConnectionError
        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.bios_upgrade()

        assert "Device not connected" in str(exc_info.value)

    def test_create_backup_success(self) -> None:
        """Test successful backup creation."""
        backup_sequence = ["/system backup save name=test", "/export file=test"]

        # Mock successful command execution
        self.mock_session.execute_command.side_effect = [
            "backup saved",
            "export created",
        ]

        # Test backup creation
        result = self.platform_ops.create_backup(backup_sequence)

        assert isinstance(result, BackupResult)
        assert result.success is True
        assert len(result.text_outputs) == 2
        assert self.mock_session.execute_command.call_count == 2
        self.mock_session.execute_command.assert_any_call(
            "/system backup save name=test"
        )
        self.mock_session.execute_command.assert_any_call("/export file=test")

    def test_create_backup_not_connected(self) -> None:
        """Test backup creation when device not connected."""
        self.mock_session.is_connected = False
        backup_sequence = ["/system backup save"]

        # Should raise DeviceConnectionError
        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.create_backup(backup_sequence)

        assert "Device not connected" in str(exc_info.value)

    def test_create_backup_command_failed(self) -> None:
        """Test backup creation when command fails."""
        backup_sequence = ["/system backup save"]

        # Mock command failure
        self.mock_session.execute_command.side_effect = DeviceExecutionError(
            "Command failed"
        )

        # Should return failed BackupResult (not raise exception)
        result = self.platform_ops.create_backup(backup_sequence)

        assert isinstance(result, BackupResult)
        assert result.success is False
        assert len(result.errors) > 0
        assert "Command failed" in str(result.errors)

    def test_create_backup_with_default_sequence(self) -> None:
        """Test backup creation with empty sequence (uses default)."""
        # Mock successful command execution
        self.mock_session.execute_command.side_effect = [
            "backup saved",
            "export created",
        ]

        # Test backup creation with empty sequence
        result = self.platform_ops.create_backup([])

        assert isinstance(result, BackupResult)
        assert result.success is True
        # Should use default sequence
        assert self.mock_session.execute_command.call_count == 2

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_firmware_upgrade_with_delays(self, mock_sleep: MagicMock) -> None:
        """Test firmware upgrade respects delay parameters."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True
        mock_firmware_path.name = "firmware.npk"

        # Mock successful upload and reboot
        self.mock_session.upload_file.return_value = True
        self.mock_session._transport.send_interactive.return_value = "reboot response"

        # Test firmware upgrade with custom delay
        result = self.platform_ops.firmware_upgrade(
            mock_firmware_path,
            pre_reboot_delay=5.0,
        )

        assert result is True
        # Should have called sleep with the specified delay
        mock_sleep.assert_called_with(5.0)

    def test_operation_support_checking(self) -> None:
        """Test that all operations are reported as supported."""
        assert self.platform_ops.is_operation_supported("firmware_upgrade") is True
        assert self.platform_ops.is_operation_supported("firmware_downgrade") is True
        assert self.platform_ops.is_operation_supported("bios_upgrade") is True
        assert self.platform_ops.is_operation_supported("create_backup") is True
        assert (
            self.platform_ops.is_operation_supported("nonexistent_operation") is False
        )
