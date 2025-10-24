# SPDX-License-Identifier: MIT
"""Tests for Cisco IOS vendor-specific backup operations."""

from unittest.mock import MagicMock

import pytest

from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
from network_toolkit.platforms.base import BackupResult
from network_toolkit.platforms.cisco_ios.operations import CiscoIOSOperations


class TestCiscoIOSBackupOperations:
    """Test Cisco IOS backup operations."""

    def test_config_backup_success(self) -> None:
        """Test successful configuration backup."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"
        mock_session.execute_command.return_value = "OK"

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test config backup
        result = ops.config_backup(backup_sequence=["show running-config"])

        assert isinstance(result, BackupResult)
        assert result.success is True
        assert len(result.text_outputs) > 0
        assert len(result.files_to_download) > 0
        # Verify the backup command was called (dir commands for file checks will also be called)
        assert any(
            "show running-config" in str(call)
            for call in mock_session.execute_command.call_args_list
        )

    def test_config_backup_disconnected(self) -> None:
        """Test configuration backup when device is disconnected."""
        # Create mock session (disconnected)
        mock_session = MagicMock()
        mock_session.is_connected = False

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test config backup should raise error
        with pytest.raises(DeviceConnectionError, match="Device not connected"):
            ops.config_backup(backup_sequence=["show running-config"])

    def test_config_backup_default_sequence(self) -> None:
        """Test configuration backup with default sequence."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test config backup with empty sequence (should use default)
        result = ops.config_backup(backup_sequence=[])

        assert isinstance(result, BackupResult)
        assert result.success is True
        # Verify the default commands were called
        assert any(
            "show running-config" in str(call)
            for call in mock_session.execute_command.call_args_list
        )

    def test_config_backup_execution_error(self) -> None:
        """Test configuration backup with execution error."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"
        mock_session.execute_command.side_effect = DeviceExecutionError(
            "Command failed"
        )

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test config backup should return BackupResult with success=False when all commands fail
        result = ops.config_backup(backup_sequence=["show running-config"])
        assert isinstance(result, BackupResult)
        assert result.success is False  # All commands failed
        assert len(result.errors) > 0

    def test_backup_success(self) -> None:
        """Test successful comprehensive backup."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"
        mock_session.execute_command.return_value = "OK"

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test comprehensive backup
        result = ops.backup(backup_sequence=["show running-config", "show version"])

        assert isinstance(result, BackupResult)
        assert result.success is True
        assert len(result.text_outputs) > 0
        # At least the 2 backup commands, plus potential file checks
        assert mock_session.execute_command.call_count >= 2

    def test_backup_disconnected(self) -> None:
        """Test comprehensive backup when device is disconnected."""
        # Create mock session (disconnected)
        mock_session = MagicMock()
        mock_session.is_connected = False

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test backup should raise error
        with pytest.raises(DeviceConnectionError, match="Device not connected"):
            ops.backup(backup_sequence=["show running-config", "show version"])

    def test_backup_default_sequence(self) -> None:
        """Test comprehensive backup with default sequence."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test backup with empty sequence (should use default)
        result = ops.backup(backup_sequence=[])

        assert isinstance(result, BackupResult)
        assert result.success is True
        # Verify default commands were called (plus file check commands)
        call_strs = [str(call) for call in mock_session.execute_command.call_args_list]
        assert any("show running-config" in s for s in call_strs)
        assert any("show startup-config" in s for s in call_strs)
        assert any("show version" in s for s in call_strs)
        assert any("show inventory" in s for s in call_strs)

    def test_backup_execution_error(self) -> None:
        """Test comprehensive backup with execution error."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"
        mock_session.execute_command.side_effect = DeviceExecutionError(
            "Command failed"
        )

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test backup should return BackupResult with errors when all commands fail
        result = ops.backup(backup_sequence=["show running-config", "show version"])
        assert isinstance(result, BackupResult)
        assert result.success is False  # All commands failed
        assert len(result.errors) > 0
