# SPDX-License-Identifier: MIT
"""Tests for MikroTik RouterOS vendor-specific backup operations."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
from network_toolkit.platforms.mikrotik_routeros.operations import MikroTikRouterOSOperations


class TestMikroTikRouterOSBackupOperations:
    """Test MikroTik RouterOS backup operations."""

    def test_config_backup_success(self) -> None:
        """Test successful configuration backup."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"
        mock_session.execute_command.return_value = "OK"

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test config backup
        result = ops.config_backup(backup_sequence=["/export file=test-config"])

        assert result is True
        mock_session.execute_command.assert_called_with("/export file=test-config")

    def test_config_backup_disconnected(self) -> None:
        """Test configuration backup when device is disconnected."""
        # Create mock session (disconnected)
        mock_session = MagicMock()
        mock_session.is_connected = False

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test config backup should raise error
        with pytest.raises(DeviceConnectionError, match="Device not connected"):
            ops.config_backup(backup_sequence=["/export file=test-config"])

    def test_config_backup_default_sequence(self) -> None:
        """Test configuration backup with default sequence."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test config backup with empty sequence (should use default)
        result = ops.config_backup(backup_sequence=[])

        assert result is True
        mock_session.execute_command.assert_called_with("/export file=nw-config-export")

    def test_config_backup_execution_error(self) -> None:
        """Test configuration backup with execution error."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.execute_command.side_effect = DeviceExecutionError("Command failed")

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test config backup should raise error
        with pytest.raises(DeviceExecutionError):
            ops.config_backup(backup_sequence=["/export file=test-config"])

    def test_backup_success(self) -> None:
        """Test successful comprehensive backup."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"
        mock_session.execute_command.return_value = "OK"

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test comprehensive backup
        result = ops.backup(backup_sequence=["/export file=test", "/system/backup/save name=test"])

        assert result is True
        assert mock_session.execute_command.call_count == 2

    def test_backup_disconnected(self) -> None:
        """Test comprehensive backup when device is disconnected."""
        # Create mock session (disconnected)
        mock_session = MagicMock()
        mock_session.is_connected = False

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test backup should raise error
        with pytest.raises(DeviceConnectionError, match="Device not connected"):
            ops.backup(backup_sequence=["/export", "/system/backup/save"])

    def test_backup_default_sequence(self) -> None:
        """Test comprehensive backup with default sequence."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "test_device"

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test backup with empty sequence (should use default)
        result = ops.backup(backup_sequence=[])

        assert result is True
        expected_calls: list[tuple[tuple[str, ...], dict[str, Any]]] = [
            (("/export file=nw-config-export",), {}),
            (("/system/backup/save name=nw-system-backup",), {}),
        ]
        assert mock_session.execute_command.call_args_list == expected_calls

    def test_backup_execution_error(self) -> None:
        """Test comprehensive backup with execution error."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.execute_command.side_effect = DeviceExecutionError("Command failed")

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test backup should raise error
        with pytest.raises(DeviceExecutionError):
            ops.backup(backup_sequence=["/export", "/system/backup/save"])

    def test_create_backup_fixed_connection_check(self) -> None:
        """Test that create_backup uses proper connection check."""
        # Create mock session (disconnected)
        mock_session = MagicMock()
        mock_session.is_connected = False

        # Create operations instance
        ops = MikroTikRouterOSOperations(mock_session)

        # Test create_backup should raise error for disconnected device
        with pytest.raises(DeviceConnectionError, match="Device not connected"):
            ops.create_backup(backup_sequence=["/export"])
