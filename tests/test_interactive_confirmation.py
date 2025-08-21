"""Tests for interactive confirmation functionality."""

from unittest.mock import Mock

import pytest

from network_toolkit.common.interactive_confirmation import (
    InteractiveConfirmationHandler,
    create_confirmation_handler,
)
from network_toolkit.exceptions import DeviceExecutionError
from network_toolkit.platforms.mikrotik_routeros.confirmation_patterns import (
    MIKROTIK_PACKAGE_DOWNGRADE,
    MIKROTIK_REBOOT,
    MIKROTIK_ROUTERBOARD_UPGRADE,
    MIKROTIK_SYSTEM_RESET,
)


class TestConfirmationPattern:
    """Test the ConfirmationPattern class."""

    def test_mikrotik_patterns(self) -> None:
        """Test MikroTik confirmation patterns are correctly defined."""
        # Test reboot pattern - this was the bug!
        assert MIKROTIK_REBOOT.prompt == "Reboot, yes? [y/N]:"
        assert MIKROTIK_REBOOT.response == "y"

        # Test package downgrade pattern
        assert (
            MIKROTIK_PACKAGE_DOWNGRADE.prompt
            == "Router will be rebooted. Continue? [y/N]:"
        )
        assert MIKROTIK_PACKAGE_DOWNGRADE.response == "y"

        # Test RouterBOARD upgrade pattern
        assert (
            MIKROTIK_ROUTERBOARD_UPGRADE.prompt
            == "Do you really want to upgrade firmware? [y/n]"
        )
        assert MIKROTIK_ROUTERBOARD_UPGRADE.response == "y"

        # Test system reset pattern
        assert MIKROTIK_SYSTEM_RESET.prompt == "Dangerous! Reset anyway? [y/N]:"
        assert MIKROTIK_SYSTEM_RESET.response == "y"

    def test_cisco_patterns(self) -> None:
        """Test Cisco confirmation patterns are correctly defined."""
        # TODO: Add Cisco patterns when cisco_iosxe/confirmation_patterns.py is created
        pass


class TestInteractiveConfirmationHandler:
    """Test the InteractiveConfirmationHandler class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_transport = Mock()
        self.handler = InteractiveConfirmationHandler(self.mock_transport)

    def test_handler_initialization(self) -> None:
        """Test handler is properly initialized."""
        # Test that we can create a handler and it works
        assert isinstance(self.handler, InteractiveConfirmationHandler)

    def test_execute_with_confirmation_success(self) -> None:
        """Test successful execution with confirmation."""
        # Mock successful response
        self.mock_transport.send_interactive.return_value = (
            "Command executed successfully"
        )

        # Execute command
        response = self.handler.execute_with_confirmation(
            command="/system/reboot",
            pattern=MIKROTIK_REBOOT,
            timeout_ops=10.0,
            description="test reboot",
        )

        # Verify result
        assert response == "Command executed successfully"

        # Verify transport was called correctly
        self.mock_transport.send_interactive.assert_called_once()
        call_args = self.mock_transport.send_interactive.call_args

        # Check interact_events
        interact_events = call_args[1]["interact_events"]
        assert len(interact_events) == 2
        assert interact_events[0] == ("/system/reboot", "Reboot, yes? [y/N]:", True)
        assert interact_events[1] == ("y", "", False)

        # Check timeout
        assert call_args[1]["timeout_ops"] == 10.0

    def test_execute_with_confirmation_reboot_disconnect(self) -> None:
        """Test that expected disconnection during reboot is handled correctly."""
        # Mock expected disconnection error
        self.mock_transport.send_interactive.side_effect = Exception(
            "timed out sending interactive input to device"
        )

        # Execute reboot command
        response = self.handler.execute_with_confirmation(
            command="/system/reboot",
            pattern=MIKROTIK_REBOOT,
            timeout_ops=10.0,
            description="test reboot",
        )

        # Should return expected message for reboot operations
        assert response == "Device rebooted (connection lost as expected)"

    def test_execute_with_confirmation_non_reboot_error(self) -> None:
        """Test that unexpected errors for non-reboot operations raise exceptions."""
        # Mock error
        self.mock_transport.send_interactive.side_effect = Exception(
            "command not found"
        )

        # Execute non-reboot command - should raise exception
        with pytest.raises(DeviceExecutionError) as exc_info:
            self.handler.execute_with_confirmation(
                command="/system/routerboard/upgrade",
                pattern=MIKROTIK_ROUTERBOARD_UPGRADE,
                timeout_ops=10.0,
                description="test upgrade",
            )

        assert "Interactive test upgrade failed" in str(exc_info.value)

    def test_execute_with_confirmation_unexpected_reboot_error(self) -> None:
        """Test that truly unexpected errors during reboot still raise exceptions."""
        # Mock unexpected error
        self.mock_transport.send_interactive.side_effect = Exception(
            "command not found"
        )

        # Execute reboot command with unexpected error
        with pytest.raises(DeviceExecutionError) as exc_info:
            self.handler.execute_with_confirmation(
                command="/system/reboot",
                pattern=MIKROTIK_REBOOT,
                timeout_ops=10.0,
                description="test reboot",
            )

        assert "Interactive test reboot failed" in str(exc_info.value)

    def test_is_reboot_operation(self) -> None:
        """Test reboot operation detection."""
        # These should be considered reboot operations
        reboot_patterns = [
            MIKROTIK_REBOOT,
            MIKROTIK_PACKAGE_DOWNGRADE,
            MIKROTIK_SYSTEM_RESET,
        ]

        for pattern in reboot_patterns:
            assert pattern.is_reboot_operation

        # This should NOT be considered a reboot operation
        non_reboot_patterns = [
            MIKROTIK_ROUTERBOARD_UPGRADE,  # The upgrade itself doesn't reboot
        ]

        for pattern in non_reboot_patterns:
            assert not pattern.is_reboot_operation

    def test_expected_disconnect_during_reboot(self) -> None:
        """Test that expected disconnection during reboot is handled properly."""
        # Mock expected disconnection errors
        expected_disconnect_errors = [
            Exception("connection lost"),
            Exception("device disconnected"),
            Exception("timeout occurred"),
            Exception("connection closed"),
            Exception("EOF reached"),
            Exception("timed out sending interactive input to device"),
            Exception("Connection reset by peer"),
        ]

        for error in expected_disconnect_errors:
            self.mock_transport.send_interactive.side_effect = error

            # For reboot operations, should return expected message
            response = self.handler.execute_with_confirmation(
                command="/system/reboot",
                pattern=MIKROTIK_REBOOT,
                timeout_ops=10.0,
                description="test reboot",
            )
            assert response == "Device rebooted (connection lost as expected)"

        # For non-reboot operations, should raise exception even with "expected" errors
        for error in expected_disconnect_errors[:3]:  # Test a few
            self.mock_transport.send_interactive.side_effect = error

            with pytest.raises(DeviceExecutionError):
                self.handler.execute_with_confirmation(
                    command="/system/routerboard/upgrade",
                    pattern=MIKROTIK_ROUTERBOARD_UPGRADE,  # This is NOT a reboot operation
                    timeout_ops=10.0,
                    description="test upgrade",
                )


class TestFactoryFunction:
    """Test the factory function."""

    def test_create_confirmation_handler(self) -> None:
        """Test the factory function creates a proper handler."""
        mock_transport = Mock()
        handler = create_confirmation_handler(mock_transport)

        assert isinstance(handler, InteractiveConfirmationHandler)
