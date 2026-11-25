"""Test CLI transport configuration."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from network_toolkit.cli import app


class TestCLITransportConfiguration:
    """Test CLI commands with transport configuration."""

    def test_run_command_with_transport_option(self, config_file: Path) -> None:
        """Run forwards the selected transport when opening the session."""
        command = "/system/identity/print"
        with patch("network_toolkit.device.DeviceSession") as session:
            connected_session = session.return_value.__enter__.return_value
            connected_session.execute_command.return_value = "identity: router"
            result = CliRunner().invoke(
                app,
                [
                    "run",
                    "test_device1",
                    command,
                    "--config",
                    str(config_file),
                    "--transport",
                    "scrapli",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "identity: router" in result.output
        session.assert_called_once()
        assert session.call_args.args[4] == "scrapli"
        connected_session.execute_command.assert_called_once_with(command)

    def test_cli_command_rejects_unknown_transport(self, config_file: Path) -> None:
        """Reject an unsupported transport before creating a tmux session."""
        with patch("network_toolkit.commands.ssh._ensure_libtmux") as tmux:
            result = CliRunner().invoke(
                app,
                [
                    "cli",
                    "test_device1",
                    "--config",
                    str(config_file),
                    "--transport",
                    "unknown-transport",
                ],
            )

        assert result.exit_code == 1, result.output
        assert "Unknown transport type: 'unknown-transport'" in result.output
        tmux.assert_not_called()

    def test_supported_types_shows_transport_info(self):
        """Test that config supported-types command shows transport information."""
        runner = CliRunner()

        result = runner.invoke(app, ["config", "supported-types"])

        # Should succeed and show transport information
        assert result.exit_code == 0
        output = result.stdout

        # Should show transport types
        assert "Transport Types" in output or "Available Transport Types" in output
        assert "scrapli" in output

        # Should show device types in supported platforms
        assert "cisco_ios" in output
        assert "cisco_nxos" in output

        # Should show transport support information
        assert "Transport Support" in output or "scrapli" in output
