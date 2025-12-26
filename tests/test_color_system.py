"""Simple tests for color system integration."""

from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.common.output import OutputMode
from network_toolkit.common.styles import StyleManager, StyleName


def test_color_system_no_color_mode() -> None:
    """Test that no-color mode works without errors."""
    runner = CliRunner()

    # Create a mock config with empty devices
    mock_config = Mock()
    mock_config.devices = {}
    mock_config.general = Mock()
    mock_config.general.output_mode = "default"
    mock_config.general.log_level = "WARNING"
    mock_config.general.enable_logging = False

    with (
        patch("network_toolkit.common.command.load_config", return_value=mock_config),
        patch("network_toolkit.commands.list.load_config", return_value=mock_config),
    ):
        # Test the command works in no-color mode
        result = runner.invoke(app, ["list", "devices", "--output-mode", "no-color"])

        # Should not crash with color errors
        assert result.exit_code == 0
        # Should not contain color markup in output
        assert "[" not in result.stdout or "No devices configured" in result.stdout


def test_color_system_default_mode() -> None:
    """Test that default color mode works."""
    from network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig

    runner = CliRunner()

    # Create proper Pydantic config objects
    general = GeneralConfig(
        output_mode="default", log_level="WARNING", enable_logging=False
    )
    device = DeviceConfig(
        host="192.168.1.1",
        port=22,
        device_type="mikrotik_routeros",
        platform="tile",
    )
    mock_config = NetworkConfig(
        devices={"test-device": device},
        device_groups={},
        general=general,
    )

    with (
        patch("network_toolkit.common.command.load_config", return_value=mock_config),
        patch("network_toolkit.commands.list.load_config", return_value=mock_config),
    ):
        # Test the command works in default mode
        result = runner.invoke(app, ["list", "devices"])

        # Should not crash
        assert result.exit_code == 0


def test_style_manager_no_color_returns_none() -> None:
    """Test that StyleManager returns None for styles in no-color mode."""
    style_manager = StyleManager(OutputMode.NO_COLOR)

    # Should return None for any style in no-color mode
    assert style_manager.get_style(StyleName.DEVICE) is None
    assert style_manager.get_style(StyleName.SUCCESS) is None
    assert style_manager.get_style(StyleName.ERROR) is None


def test_style_manager_default_returns_styles() -> None:
    """Test that StyleManager returns styles in default mode."""
    style_manager = StyleManager(OutputMode.DEFAULT)

    # Should return actual styles in default mode
    assert style_manager.get_style(StyleName.DEVICE) is not None
    assert style_manager.get_style(StyleName.SUCCESS) is not None
    assert style_manager.get_style(StyleName.ERROR) is not None


def test_style_manager_creates_table() -> None:
    """Test that StyleManager can create tables without errors."""
    style_manager = StyleManager(OutputMode.DEFAULT)

    # Should create table without errors
    table = style_manager.create_table("Test Table")
    assert table is not None

    # Should add columns without errors
    style_manager.add_column(table, "Name", StyleName.DEVICE)
    style_manager.add_column(table, "Status", StyleName.SUCCESS)


def test_all_output_modes_work() -> None:
    """Test that all output modes can be initialized."""
    for mode in OutputMode:
        style_manager = StyleManager(mode)
        assert style_manager is not None

        # All modes should be able to create tables
        table = style_manager.create_table("Test")
        assert table is not None
