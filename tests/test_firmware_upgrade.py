"""Tests for firmware_upgrade command module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from network_toolkit.commands.firmware_upgrade import register


class TestFirmwareUpgrade:
    """Test firmware upgrade command functionality."""

    def test_register_command(self) -> None:
        """Test that the command is properly registered."""
        app = typer.Typer()

        # Should not raise exception
        register(app)

        # Verify the module can be imported and register function exists
        assert callable(register)

    @patch("network_toolkit.commands.firmware_upgrade.setup_logging")
    @patch("network_toolkit.commands.firmware_upgrade.load_config")
    @patch("network_toolkit.commands.firmware_upgrade.import_module")
    @patch("network_toolkit.commands.firmware_upgrade.console")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_firmware_upgrade_command_execution(
        self,
        mock_is_file: MagicMock,
        mock_exists: MagicMock,
        mock_console: MagicMock,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test firmware upgrade command execution through CLI runner."""
        # Mock file validation to pass
        mock_exists.return_value = True
        mock_is_file.return_value = True

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

        # Test basic command execution with required firmware file
        runner.invoke(app, ["test_device", "firmware.npk"])

        # The command should at least attempt to load config and setup logging
        mock_setup_logging.assert_called()
        mock_load_config.assert_called()

    @patch("network_toolkit.commands.firmware_upgrade.setup_logging")
    @patch("network_toolkit.commands.firmware_upgrade.load_config")
    @patch("network_toolkit.commands.firmware_upgrade.import_module")
    @patch("network_toolkit.commands.firmware_upgrade.console")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_firmware_upgrade_with_options(
        self,
        mock_is_file: MagicMock,
        mock_exists: MagicMock,
        mock_console: MagicMock,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test firmware upgrade with various options."""
        # Mock file validation to pass
        mock_exists.return_value = True
        mock_is_file.return_value = True

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
        runner.invoke(
            app, ["test_device", "firmware.npk", "--skip-precheck", "--verbose"]
        )

        mock_setup_logging.assert_called()
        mock_load_config.assert_called()

    @patch("network_toolkit.commands.firmware_upgrade.setup_logging")
    @patch("network_toolkit.commands.firmware_upgrade.load_config")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_firmware_upgrade_config_error(
        self,
        mock_is_file: MagicMock,
        mock_exists: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test firmware upgrade with configuration error."""
        # Mock file validation to pass
        mock_exists.return_value = True
        mock_is_file.return_value = True

        # Mock load_config to raise exception
        from network_toolkit.exceptions import ConfigurationError

        mock_load_config.side_effect = ConfigurationError("Config error")

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test command execution with config error
        result = runner.invoke(app, ["test_device", "firmware.npk"])

        # Should have called these functions before config error
        mock_setup_logging.assert_called()
        mock_load_config.assert_called()
        # Exit code should be 1 due to error
        assert result.exit_code == 1

    @patch("network_toolkit.commands.firmware_upgrade.setup_logging")
    @patch("network_toolkit.commands.firmware_upgrade.load_config")
    @patch("network_toolkit.commands.firmware_upgrade.import_module")
    @patch("network_toolkit.commands.firmware_upgrade.console")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_firmware_upgrade_with_custom_config(
        self,
        mock_is_file: MagicMock,
        mock_exists: MagicMock,
        mock_console: MagicMock,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test firmware upgrade with custom config file."""
        # Mock file validation to pass
        mock_exists.return_value = True
        mock_is_file.return_value = True

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

        # Test with custom config file
        runner.invoke(
            app, ["test_device", "firmware.npk", "--config", "custom_config.yml"]
        )

        mock_setup_logging.assert_called()
        mock_load_config.assert_called_with(Path("custom_config.yml"))

    @patch("network_toolkit.commands.firmware_upgrade.setup_logging")
    @patch("network_toolkit.commands.firmware_upgrade.load_config")
    @patch("network_toolkit.commands.firmware_upgrade.import_module")
    @patch("network_toolkit.commands.firmware_upgrade.console")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_firmware_upgrade_group_processing(
        self,
        mock_is_file: MagicMock,
        mock_exists: MagicMock,
        mock_console: MagicMock,
        mock_import: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test firmware upgrade with device group."""
        # Mock file validation to pass
        mock_exists.return_value = True
        mock_is_file.return_value = True

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
        runner.invoke(app, ["test_group", "firmware.npk"])

        mock_setup_logging.assert_called()
        mock_load_config.assert_called()

    def test_firmware_upgrade_file_validation(self) -> None:
        """Test firmware upgrade with invalid file."""
        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with non-existent file (Path.exists will return False by default)
        result = runner.invoke(app, ["test_device", "nonexistent.npk"])

        # Should exit with error code 1
        assert result.exit_code == 1

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_firmware_upgrade_wrong_extension(
        self,
        mock_is_file: MagicMock,
        mock_exists: MagicMock,
    ) -> None:
        """Test firmware upgrade with wrong file extension."""
        # Mock file exists but has wrong extension
        mock_exists.return_value = True
        mock_is_file.return_value = True

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with wrong extension
        result = runner.invoke(app, ["test_device", "firmware.txt"])

        # Should exit with error code 1
        assert result.exit_code == 1
