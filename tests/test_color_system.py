"""Simple tests for color system integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.common.output import OutputMode
from network_toolkit.common.styles import StyleManager, StyleName


def test_color_system_no_color_mode(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit no-color mode keeps ANSI out of rendered tables."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NW_OUTPUT_MODE", "dark")
    monkeypatch.setenv("TERM", "xterm-256color")

    result = CliRunner().invoke(
        app,
        ["list", "devices", "--config", str(config_file), "--output-mode", "no-color"],
        color=True,
    )

    assert result.exit_code == 0, result.output
    assert "test_device1" in result.stdout
    assert "\x1b[" not in result.stdout


def test_color_system_default_mode(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default output detects whether a terminal was requested."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NW_OUTPUT_MODE", raising=False)
    monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    args = ["list", "devices", "--config", str(config_file)]

    redirected = CliRunner().invoke(app, args, color=True)
    assert redirected.exit_code == 0, redirected.output
    assert "test_device1" in redirected.stdout
    assert "\x1b[" not in redirected.stdout

    monkeypatch.setenv("FORCE_COLOR", "1")
    forced = CliRunner().invoke(app, args, color=True)
    assert forced.exit_code == 0, forced.output
    assert "test_device1" in forced.stdout
    assert "\x1b[" in forced.stdout


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
