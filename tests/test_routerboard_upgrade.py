"""Tests for routerboard_upgrade command module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from network_toolkit.commands.routerboard_upgrade import register


class TestRouterboardUpgrade:
    """Test routerboard upgrade command functionality."""

    def test_register_command(self) -> None:
        """Test that the command is properly registered."""
        app = typer.Typer()

        # Should not raise exception
        register(app)

        # Verify the module can be imported and register function exists
        assert callable(register)

    @patch("network_toolkit.commands.routerboard_upgrade.setup_logging")
    @patch("network_toolkit.commands.routerboard_upgrade.load_config")
    @patch("network_toolkit.api.routerboard_upgrade.upgrade_routerboard")
    def test_routerboard_upgrade_command_execution(
        self,
        mock_upgrade: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test routerboard upgrade command execution through CLI runner."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.devices = {"test_device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock upgrade result
        mock_result = MagicMock()
        mock_result.success_count = 1
        mock_result.failed_count = 0
        mock_result.results = [MagicMock(success=True, platform="mikrotik_routeros")]
        mock_upgrade.return_value = mock_result

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test basic command execution
        runner.invoke(app, ["test_device"])

        # The command should at least attempt to load config and setup logging
        mock_setup_logging.assert_called()
        mock_load_config.assert_called()
        mock_upgrade.assert_called()

    @patch("network_toolkit.commands.routerboard_upgrade.setup_logging")
    @patch("network_toolkit.commands.routerboard_upgrade.load_config")
    @patch("network_toolkit.api.routerboard_upgrade.upgrade_routerboard")
    def test_routerboard_upgrade_with_options(
        self,
        mock_upgrade: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test routerboard upgrade with various options."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.devices = {"test_device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock upgrade result
        mock_result = MagicMock()
        mock_result.success_count = 1
        mock_result.failed_count = 0
        mock_result.results = []
        mock_upgrade.return_value = mock_result

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with options
        runner.invoke(app, ["test_device", "--skip-precheck", "--verbose"])

        mock_setup_logging.assert_called()
        mock_load_config.assert_called()
        mock_upgrade.assert_called()

    @patch("network_toolkit.commands.routerboard_upgrade.setup_logging")
    @patch("network_toolkit.commands.routerboard_upgrade.load_config")
    def test_routerboard_upgrade_config_error(
        self,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test routerboard upgrade with configuration error."""
        # Mock load_config to raise exception
        from network_toolkit.exceptions import ConfigurationError

        mock_load_config.side_effect = ConfigurationError("Config error")

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test command execution with config error
        result = runner.invoke(app, ["test_device"])

        # Should have called these functions before config error
        mock_setup_logging.assert_called()
        mock_load_config.assert_called()
        # Exit code should be 1 due to error
        assert result.exit_code == 1

    @patch("network_toolkit.commands.routerboard_upgrade.setup_logging")
    @patch("network_toolkit.commands.routerboard_upgrade.load_config")
    @patch("network_toolkit.api.routerboard_upgrade.upgrade_routerboard")
    def test_routerboard_upgrade_with_custom_config(
        self,
        mock_upgrade: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test routerboard upgrade with custom config file."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.devices = {"test_device": MagicMock()}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock upgrade result
        mock_result = MagicMock()
        mock_result.success_count = 1
        mock_result.failed_count = 0
        mock_result.results = []
        mock_upgrade.return_value = mock_result

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with custom config file
        runner.invoke(app, ["test_device", "--config", "custom_config.yml"])

        mock_setup_logging.assert_called()
        mock_load_config.assert_called_with(Path("custom_config.yml"))

    @patch("network_toolkit.commands.routerboard_upgrade.setup_logging")
    @patch("network_toolkit.commands.routerboard_upgrade.load_config")
    @patch("network_toolkit.api.routerboard_upgrade.upgrade_routerboard")
    def test_routerboard_upgrade_group_processing(
        self,
        mock_upgrade: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test routerboard upgrade with device group."""
        # Setup mocks for group
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_config.device_groups = {"test_group": MagicMock()}
        mock_load_config.return_value = mock_config

        # Mock upgrade result
        mock_result = MagicMock()
        mock_result.success_count = 2
        mock_result.failed_count = 0
        mock_result.results = []
        mock_upgrade.return_value = mock_result

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with group
        runner.invoke(app, ["test_group"])

        mock_setup_logging.assert_called()
        mock_load_config.assert_called()
        mock_upgrade.assert_called()

    @patch("network_toolkit.commands.routerboard_upgrade.setup_logging")
    @patch("network_toolkit.commands.routerboard_upgrade.load_config")
    @patch("network_toolkit.api.routerboard_upgrade.upgrade_routerboard")
    def test_routerboard_upgrade_device_not_found(
        self,
        mock_upgrade: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
    ) -> None:
        """Test routerboard upgrade with device not found."""
        # Setup mocks with empty devices and groups
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        # Mock upgrade result to raise exception or return failure
        from network_toolkit.exceptions import NetworkToolkitError

        mock_upgrade.side_effect = NetworkToolkitError("Target not found")

        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test with non-existent device
        result = runner.invoke(app, ["nonexistent_device"])

        mock_setup_logging.assert_called()
        mock_load_config.assert_called()
        # Should exit with error code 1
        assert result.exit_code == 1

    def test_routerboard_upgrade_help(self) -> None:
        """Test routerboard upgrade command help."""
        # Create app and register command
        app = typer.Typer()
        register(app)

        runner = CliRunner()

        # Test help command
        result = runner.invoke(app, ["--help"])

        # Should exit with code 0 and show help
        assert result.exit_code == 0
        assert (
            "routerboard-upgrade" in result.output or "upgrade" in result.output.lower()
        )
