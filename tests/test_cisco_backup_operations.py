# SPDX-License-Identifier: MIT
"""Tests for Cisco IOS vendor-specific backup operations."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
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

        assert result is True
        mock_session.execute_command.assert_called_with("show running-config")

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

        assert result is True
        mock_session.execute_command.assert_called_with("show running-config")

    def test_config_backup_execution_error(self) -> None:
        """Test configuration backup with execution error."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.execute_command.side_effect = DeviceExecutionError("Command failed")

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test config backup should raise error
        with pytest.raises(DeviceExecutionError):
            ops.config_backup(backup_sequence=["show running-config"])

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

        assert result is True
        assert mock_session.execute_command.call_count == 2

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

        assert result is True
        expected_calls: list[tuple[tuple[str, ...], dict[str, Any]]] = [
            (("show running-config",), {}),
            (("show startup-config",), {}),
            (("show version",), {}),
            (("show inventory",), {}),
        ]
        assert mock_session.execute_command.call_args_list == expected_calls

    def test_backup_execution_error(self) -> None:
        """Test comprehensive backup with execution error."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.execute_command.side_effect = DeviceExecutionError("Command failed")

        # Create operations instance
        ops = CiscoIOSOperations(mock_session)

        # Test backup should raise error
        with pytest.raises(DeviceExecutionError):
            ops.backup(backup_sequence=["show running-config", "show version"])
