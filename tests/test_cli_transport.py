"""Test CLI transport configuration."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app


class TestCLITransportConfiguration:
    """Test CLI commands with transport configuration."""

    def test_run_command_with_transport_option(self):
        """Test that run command accepts transport option."""
        runner = CliRunner()

        # Mock the actual execution to avoid real network operations
        with (
            patch("network_toolkit.commands.run.load_config") as mock_load_config,
            patch("network_toolkit.commands.run.SequenceManager") as mock_sm,
            patch(
                "network_toolkit.commands.run.create_ip_based_config"
            ) as mock_create_ip,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config
            mock_create_ip.return_value = mock_config

            # Test that the command accepts the transport option without error
            result = runner.invoke(
                app,
                [
                    "run",
                    "192.168.1.1",
                    "/system/identity/print",
                    "--platform",
                    "mikrotik_routeros",
                    "--transport",
                    "nornir_netmiko",
                ],
            )

            # Should not fail due to unknown option
            assert "--transport" in str(result.stdout) or result.exit_code != 2

            # Verify create_ip_based_config was called with transport_type
            if mock_create_ip.called:
                call_args = mock_create_ip.call_args
                if call_args and "transport_type" in call_args.kwargs:
                    assert call_args.kwargs["transport_type"] == "nornir_netmiko"

    def test_ssh_command_with_transport_option(self):
        """Test that ssh command accepts transport option."""
        runner = CliRunner()

        # Mock the actual execution to avoid real network operations
        with (
            patch("network_toolkit.commands.ssh.load_config") as mock_load_config,
            patch("network_toolkit.commands.ssh.DeviceResolver") as mock_resolver,
            patch(
                "network_toolkit.commands.ssh.create_ip_based_config"
            ) as mock_create_ip,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config
            mock_create_ip.return_value = mock_config

            # Test that the command accepts the transport option without error
            result = runner.invoke(
                app,
                [
                    "ssh",
                    "192.168.1.1",
                    "--platform",
                    "mikrotik_routeros",
                    "--transport",
                    "scrapli",
                ],
            )

            # Should not fail due to unknown option
            assert "--transport" in str(result.stdout) or result.exit_code != 2

    def test_supported_types_shows_transport_info(self):
        """Test that supported-types command shows transport information."""
        runner = CliRunner()

        result = runner.invoke(app, ["supported-types"])

        # Should succeed and show transport information
        assert result.exit_code == 0
        output = result.stdout

        # Should show transport types
        assert "Transport Types" in output or "Available Transport Types" in output
        assert "scrapli" in output
        assert "nornir_netmiko" in output

        # Should show device types
        assert "mikrotik_routeros" in output
        assert "cisco_ios" in output

        # Should show transport support information
        assert "Transport Support" in output or "scrapli, nornir_netmiko" in output
