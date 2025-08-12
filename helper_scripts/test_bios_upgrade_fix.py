#!/usr/bin/env python3
"""Test script to verify the BIOS upgrade fix."""

import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, "src")

from network_toolkit.config import DeviceConfig
from network_toolkit.device import DeviceSession


def test_routerboard_upgrade_interactive():
    """Test that RouterBOARD upgrade now uses interactive command handling."""

    # Create a mock device config
    device_config = DeviceConfig(host="192.168.1.1", vendor="mikrotik", model="hAP ac²")

    # Create a device session
    device = DeviceSession("test-device", device_config)

    # Mock the transport layer
    mock_transport = MagicMock()
    device._transport = mock_transport
    device._connected = True

    # Mock the send_interactive method
    mock_transport.send_interactive.return_value = "RouterBOARD upgraded successfully"

    # Test that upgrade_routerboard uses send_interactive
    try:
        result = device.upgrade_routerboard(
            verify_before=False, pre_reboot_delay=0, confirmation_timeout=30
        )

        # Verify send_interactive was called with the correct parameters
        mock_transport.send_interactive.assert_called()
        call_args = mock_transport.send_interactive.call_args

        # Check the interact_events parameter
        interact_events = call_args[1]["interact_events"]

        # Verify the upgrade command and prompt
        assert interact_events[0][0] == "/system/routerboard/upgrade"
        assert "Do you really want to upgrade firmware? [y/n]" in interact_events[0][1]
        assert interact_events[0][2] == True  # hidden=True

        # Verify the confirmation response
        assert interact_events[1][0] == "y"
        assert interact_events[1][1] == ""
        assert interact_events[1][2] == False  # hidden=False

        print("✅ BIOS upgrade fix verified!")
        print("✅ RouterBOARD upgrade now uses interactive command handling")
        print(
            "✅ Correct prompt pattern is expected: 'Do you really want to upgrade firmware? [y/n]'"
        )
        print("✅ Automatic 'y' confirmation is sent")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_routerboard_upgrade_interactive()
    sys.exit(0 if success else 1)
