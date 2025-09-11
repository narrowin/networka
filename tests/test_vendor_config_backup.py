# SPDX-License-Identifier: MIT
"""Tests for vendor-specific config-backup command."""

from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from network_toolkit.commands.vendor_config_backup import register


class TestVendorConfigBackup:
    """Test vendor-specific config backup command functionality."""

    def test_register_command(self) -> None:
        """Test that the command is properly registered."""
        app = typer.Typer()
        register(app)

        # Check if command was registered
        assert len(app.registered_commands) > 0

    @patch("network_toolkit.commands.vendor_config_backup.load_config")
    @patch("network_toolkit.commands.vendor_config_backup.import_module")
    def test_config_backup_command_execution(
        self,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test config backup command execution through CLI runner."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.devices = {"test_device": MagicMock()}
        mock_config.device_groups = {}
        mock_config.global_command_sequences = {
            "config_backup": MagicMock(commands=["/export file=test"])
        }
        mock_load_config.return_value = mock_config

        mock_module = MagicMock()
        mock_device_session = MagicMock()
        mock_module.DeviceSession = mock_device_session
        mock_import.return_value = mock_module

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test basic command execution
        runner.invoke(app, ["test_device"])

    @patch("network_toolkit.commands.vendor_config_backup.setup_logging")
    @patch("network_toolkit.commands.vendor_config_backup.load_config")
    @patch("network_toolkit.commands.vendor_config_backup.import_module")
    def test_config_backup_with_options(
        self,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test config backup with various options."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.devices = {"test_device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        mock_module = MagicMock()
        mock_device_session = MagicMock()
        mock_module.DeviceSession = mock_device_session
        mock_import.return_value = mock_module

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with options
        runner.invoke(app, ["test_device", "--download", "--verbose"])

    @patch("network_toolkit.commands.vendor_config_backup.setup_logging")
    @patch("network_toolkit.commands.vendor_config_backup.load_config")
    def test_config_backup_config_error(
        self,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test config backup with configuration error."""
        from network_toolkit.exceptions import ConfigurationError

        mock_load_config.side_effect = ConfigurationError("Config error")

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test command execution with config error
        result = runner.invoke(app, ["test_device"])

        assert result.exit_code != 0

    @patch("network_toolkit.commands.vendor_config_backup.setup_logging")
    @patch("network_toolkit.commands.vendor_config_backup.load_config")
    @patch("network_toolkit.commands.vendor_config_backup.import_module")
    def test_config_backup_with_custom_config(
        self,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test config backup with custom config file."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.devices = {"test_device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        mock_module = MagicMock()
        mock_device_session = MagicMock()
        mock_module.DeviceSession = mock_device_session
        mock_import.return_value = mock_module

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with custom config path
        runner.invoke(app, ["test_device", "-c", "/custom/config.yml"])

    @patch("network_toolkit.commands.vendor_config_backup.setup_logging")
    @patch("network_toolkit.commands.vendor_config_backup.load_config")
    @patch("network_toolkit.commands.vendor_config_backup.import_module")
    def test_config_backup_group_processing(
        self,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test config backup with device group."""
        # Setup mocks for group
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_config.device_groups = {"test_group": MagicMock()}
        mock_load_config.return_value = mock_config

        mock_module = MagicMock()
        mock_device_session = MagicMock()
        mock_module.DeviceSession = mock_device_session
        mock_import.return_value = mock_module

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with group
        runner.invoke(app, ["test_group"])

    @patch("network_toolkit.commands.vendor_config_backup.setup_logging")
    @patch("network_toolkit.commands.vendor_config_backup.load_config")
    @patch("network_toolkit.commands.vendor_config_backup.import_module")
    def test_config_backup_device_not_found(
        self,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test config backup with device not found."""
        # Setup mocks with empty devices and groups
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        mock_module = MagicMock()
        mock_device_session = MagicMock()
        mock_module.DeviceSession = mock_device_session
        mock_import.return_value = mock_module

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with non-existent device
        result = runner.invoke(app, ["nonexistent_device"])

        assert result.exit_code != 0

    def test_config_backup_help(self) -> None:
        """Test config backup command help."""
        app = typer.Typer()
        register(app)

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "config-backup" in result.output
