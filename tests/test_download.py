"""Tests for download command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.commands.download import register
from network_toolkit.exceptions import NetworkToolkitError


class TestDownload:
    """Test download command functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_register_command(self) -> None:
        """Test that the command is properly registered."""
        app = typer.Typer()

        # Should not raise exception
        register(app)

        # Verify the module can be imported and register function exists
        assert callable(register)

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_device_success(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test successful file download from a device."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {"test-device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock device session
        mock_session = MagicMock()
        mock_session.download_file.return_value = True
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = self.runner.invoke(
            app,
            [
                "download",
                "test-device",
                "backup.rsc",
                "/tmp/backup.rsc",
                "--config",
                "test_config.yml",
            ],
        )

        assert result.exit_code == 0
        assert "Download successful!" in result.output
        mock_session.download_file.assert_called_once_with(
            remote_filename="backup.rsc",
            local_path=Path("/tmp/backup.rsc"),
            delete_remote=False,
            verify_download=True,
        )

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_device_with_options(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test file download from a device with delete and no-verify options."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {"test-device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock device session
        mock_session = MagicMock()
        mock_session.download_file.return_value = True
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = self.runner.invoke(
            app,
            [
                "download",
                "test-device",
                "backup.rsc",
                "/tmp/backup.rsc",
                "--delete-remote",
                "--no-verify",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert "Download successful!" in result.output
        mock_session.download_file.assert_called_once_with(
            remote_filename="backup.rsc",
            local_path=Path("/tmp/backup.rsc"),
            delete_remote=True,
            verify_download=False,
        )

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_device_failure(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test failed file download from a device."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {"test-device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock device session
        mock_session = MagicMock()
        mock_session.download_file.return_value = False
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = self.runner.invoke(
            app, ["download", "test-device", "backup.rsc", "/tmp/backup.rsc"]
        )

        assert result.exit_code == 1
        assert "Download failed!" in result.output

    @patch("network_toolkit.commands.download.load_config")
    def test_download_device_not_found(self, mock_load_config: MagicMock) -> None:
        """Test download command with non-existent device."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(
            app, ["download", "unknown-device", "backup.rsc", "/tmp/backup.rsc"]
        )

        assert result.exit_code == 1
        assert "not found as device or group" in result.output

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_group_success(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test successful file download from a device group."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {
            "device1": MagicMock(),
            "device2": MagicMock(),
        }
        mock_group = MagicMock()
        mock_group.members = ["device1", "device2"]
        mock_config.device_groups = {"test-group": mock_group}
        mock_config.get_group_members.return_value = ["device1", "device2"]
        mock_load_config.return_value = mock_config

        # Mock device sessions
        mock_session = MagicMock()
        mock_session.download_file.return_value = True
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = self.runner.invoke(
            app, ["download", "test-group", "backup.rsc", "/tmp/backups"]
        )

        assert result.exit_code == 0
        # Check that success count is present (Rich may format it with colors)
        assert "Successful:" in result.output
        assert "2" in result.output  # Check for the success count
        assert mock_session.download_file.call_count == 2

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_group_partial_failure(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test file download from a device group with partial failures."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {
            "device1": MagicMock(),
            "device2": MagicMock(),
        }
        mock_group = MagicMock()
        mock_group.members = ["device1", "device2"]
        mock_config.device_groups = {"test-group": mock_group}
        mock_config.get_group_members.return_value = ["device1", "device2"]
        mock_load_config.return_value = mock_config

        # Mock device sessions - first succeeds, second fails
        mock_session = MagicMock()
        mock_session.download_file.side_effect = [True, False]
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = self.runner.invoke(
            app, ["download", "test-group", "backup.rsc", "/tmp/backups"]
        )

        assert result.exit_code == 1
        # Check that success and failure counts are present (Rich may format with colors)
        assert "Successful:" in result.output
        assert "Failed:" in result.output
        assert "1" in result.output  # Check for the counts

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_group_with_exception(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test file download from a device group with exception during download."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {"device1": MagicMock()}
        mock_group = MagicMock()
        mock_group.members = ["device1"]
        mock_config.device_groups = {"test-group": mock_group}
        mock_config.get_group_members.return_value = ["device1"]
        mock_load_config.return_value = mock_config

        # Mock device session to raise exception
        mock_session_class.return_value.__enter__.side_effect = Exception(
            "Connection failed"
        )

        result = self.runner.invoke(
            app, ["download", "test-group", "backup.rsc", "/tmp/backups"]
        )

        assert result.exit_code == 1
        assert "error during download" in result.output

    @patch("network_toolkit.commands.download.load_config")
    def test_download_group_no_members(self, mock_load_config: MagicMock) -> None:
        """Test download command with group that has no members."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_group = MagicMock()
        mock_group.members = []
        mock_config.device_groups = {"empty-group": mock_group}
        mock_config.get_group_members.side_effect = Exception("No members")
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(
            app, ["download", "empty-group", "backup.rsc", "/tmp/backups"]
        )

        assert result.exit_code == 1
        assert "No devices found in group" in result.output

    @patch("network_toolkit.commands.download.load_config")
    def test_download_group_fallback_members(self, mock_load_config: MagicMock) -> None:
        """Test download command with group when get_group_members fails."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_group = MagicMock()
        mock_group.members = None
        mock_config.device_groups = {"test-group": mock_group}
        mock_config.get_group_members.side_effect = Exception("Method failed")
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(
            app, ["download", "test-group", "backup.rsc", "/tmp/backups"]
        )

        assert result.exit_code == 1
        assert "No devices found in group" in result.output

    @patch("network_toolkit.commands.download.load_config")
    def test_download_config_error(self, mock_load_config: MagicMock) -> None:
        """Test download command with configuration loading error."""
        mock_load_config.side_effect = NetworkToolkitError("Config file not found")

        result = self.runner.invoke(
            app, ["download", "test-device", "backup.rsc", "/tmp/backup.rsc"]
        )

        assert result.exit_code == 1
        assert "Config file not found" in result.output

    @patch("network_toolkit.commands.download.load_config")
    def test_download_config_error_with_details(
        self, mock_load_config: MagicMock
    ) -> None:
        """Test download command with configuration error that has details."""
        error = NetworkToolkitError("Config file not found")
        error.details = {"file_path": "/nonexistent/path"}
        mock_load_config.side_effect = error

        result = self.runner.invoke(
            app,
            ["download", "test-device", "backup.rsc", "/tmp/backup.rsc", "--verbose"],
        )

        assert result.exit_code == 1
        assert "Config file not found" in result.output

    @patch("network_toolkit.commands.download.load_config")
    def test_download_unexpected_error(self, mock_load_config: MagicMock) -> None:
        """Test download command with unexpected error."""
        mock_load_config.side_effect = ValueError("Unexpected error")

        result = self.runner.invoke(
            app, ["download", "test-device", "backup.rsc", "/tmp/backup.rsc"]
        )

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    def test_download_help(self) -> None:
        """Test download command help."""
        result = self.runner.invoke(app, ["download", "--help"])
        assert result.exit_code == 0
        assert "Download a file from a device" in result.output
        assert "--delete-remote" in result.output
        assert "--verify" in result.output

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_output_formatting(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test download command output formatting and status messages."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {"test-device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock device session
        mock_session = MagicMock()
        mock_session.download_file.return_value = True
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = self.runner.invoke(
            app, ["download", "test-device", "backup.rsc", "/tmp/backup.rsc"]
        )

        assert result.exit_code == 0
        # Check that output contains expected formatting elements
        assert "File Download Details:" in result.output
        assert "Device:" in result.output
        assert "Remote file:" in result.output
        assert "Local path:" in result.output
        assert "Delete remote after download:" in result.output
        assert "Verify download:" in result.output

    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.cli.DeviceSession")
    def test_download_group_output_formatting(
        self, mock_session_class: MagicMock, mock_load_config: MagicMock
    ) -> None:
        """Test download command group output formatting."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.devices = {"device1": MagicMock()}
        mock_group = MagicMock()
        mock_group.members = ["device1"]
        mock_config.device_groups = {"test-group": mock_group}
        mock_config.get_group_members.return_value = ["device1"]
        mock_load_config.return_value = mock_config

        # Mock device session
        mock_session = MagicMock()
        mock_session.download_file.return_value = True
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = self.runner.invoke(
            app, ["download", "test-group", "backup.rsc", "/tmp/backups"]
        )

        assert result.exit_code == 0
        # Check that group output contains expected formatting elements
        assert "Group File Download Details:" in result.output
        assert "Group:" in result.output
        assert "Devices:" in result.output
        assert "Base path:" in result.output
        assert "Group Download Results:" in result.output

    # Legacy tests for backward compatibility
    @patch("network_toolkit.commands.download.setup_logging")
    @patch("network_toolkit.commands.download.load_config")
    @patch("network_toolkit.commands.download.import_module")
    @patch("network_toolkit.commands.download.console")
    def test_download_command_execution(
        self,
        mock_console: MagicMock,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test download command execution through CLI runner."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_module = MagicMock()
        mock_import.return_value = mock_module

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test basic command execution with required parameters
        runner.invoke(app, ["test_device", "/remote/file.txt", "/local/file.txt"])

        # The command should at least attempt to load config and setup logging
        mock_setup_logging.assert_called()
        mock_load_config.assert_called()

    def test_import_functionality(self) -> None:
        """Test that the module can be imported successfully."""
        import network_toolkit.commands.download as module

        assert hasattr(module, "register")
        assert callable(module.register)
