# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Test suite for OutputManager functionality."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any
from unittest.mock import patch

import pytest

from network_toolkit.common.output import (
    OutputManager,
    OutputMode,
    get_output_manager,
    get_output_mode_from_env,
    set_output_mode,
)


class TestOutputMode:
    """Test OutputMode enum."""

    def test_output_mode_values(self) -> None:
        """Test OutputMode enum values."""
        assert OutputMode.DEFAULT.value == "default"
        assert OutputMode.LIGHT.value == "light"
        assert OutputMode.DARK.value == "dark"
        assert OutputMode.NO_COLOR.value == "no-color"
        assert OutputMode.RAW.value == "raw"


class TestOutputManager:
    """Test OutputManager class."""

    def test_normal_mode_creation(self) -> None:
        """Test creating output manager in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        assert manager.mode == OutputMode.DEFAULT
        assert manager.console is not None

    def test_raw_mode_creation(self) -> None:
        """Test creating output manager in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        assert manager.mode == OutputMode.RAW
        assert manager.console.color_system is None

    def test_no_color_mode_creation(self) -> None:
        """Test creating output manager in no-color mode."""
        manager = OutputManager(OutputMode.NO_COLOR)
        assert manager.mode == OutputMode.NO_COLOR
        assert manager.console.color_system is None


class TestOutputManagerRawMode:
    """Test OutputManager raw mode behavior."""

    def test_raw_device_output(self) -> None:
        """Test device output in raw mode."""
        manager = OutputManager(OutputMode.RAW)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            manager.print_command_output(
                "sw-acc1", "/system/clock/print", "output text"
            )
            output = mock_stdout.getvalue()

        assert "device=sw-acc1 cmd=/system/clock/print" in output
        assert "output text" in output

    def test_raw_error_message(self) -> None:
        """Test error message in raw mode."""
        manager = OutputManager(OutputMode.RAW)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            manager.print_error("Something failed", "sw-acc1")
            output = mock_stdout.getvalue()

        assert "device=sw-acc1 error: Something failed" in output

    def test_raw_summary_skipped(self) -> None:
        """Test that summaries are skipped in raw mode."""
        manager = OutputManager(OutputMode.RAW)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            manager.print_summary(
                target="sw-acc1",
                operation_type="Command",
                name="test_command",
                duration=1.5,
            )
            output = mock_stdout.getvalue()

        # Raw mode should not print summaries
        assert output == ""

    def test_raw_results_directory_skipped(self) -> None:
        """Test that results directory info is skipped in raw mode."""
        manager = OutputManager(OutputMode.RAW)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            manager.print_results_directory("/path/to/results")
            output = mock_stdout.getvalue()

        # Raw mode should not print results directory info
        assert output == ""

    def test_raw_json_output(self) -> None:
        """Test JSON output in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        test_data = {"device": "sw-acc1", "status": "success"}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            manager.print_json(test_data)
            output = mock_stdout.getvalue()

        # Should be valid JSON
        parsed = json.loads(output.strip())
        assert parsed == test_data


class TestOutputManagerNormalModes:
    """Test OutputManager normal mode behaviors."""

    def test_normal_mode_console_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that normal mode uses console output."""
        manager = OutputManager(OutputMode.DEFAULT)

        manager.print_success("Test success")
        manager.print_error("Test error")
        manager.print_warning("Test warning")
        manager.print_info("Test info")
        manager.print_command_output(
            "sw-acc1", "/system/identity/print", "[red]literal[/output]"
        )
        output = capsys.readouterr().out
        assert "Test success" in output
        assert "Test error" in output
        assert "Test warning" in output
        assert "Test info" in output
        assert "[red]literal[/output]" in output

    def test_no_color_mode_console_output(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that no-color mode uses console without colors."""
        monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("NW_OUTPUT_MODE", "dark")
        monkeypatch.setenv("TERM", "xterm-256color")
        manager = OutputManager(get_output_mode_from_env())

        manager.print_text("[red]Styled text[/red]")

        assert manager.mode is OutputMode.NO_COLOR
        assert capsys.readouterr().out == "Styled text\n"

    def test_summary_printed_in_normal_mode(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that summaries are printed in normal modes."""
        manager = OutputManager(OutputMode.DEFAULT)

        manager.print_summary(
            target="sw-acc1",
            operation_type="Command",
            name="test_command",
            duration=1.5,
        )
        output = capsys.readouterr().out
        assert "sw-acc1" in output
        assert "test_command" in output

    def test_results_directory_printed_in_normal_mode(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that results directory is printed in normal modes."""
        monkeypatch.setenv("NO_COLOR", "1")
        manager = OutputManager(get_output_mode_from_env())

        manager.print_results_directory("/path/to/results")
        assert "/path/to/results" in capsys.readouterr().out


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_no_color_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test NO_COLOR environment variable detection."""
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("NW_OUTPUT_MODE", "raw")
        assert get_output_mode_from_env() is OutputMode.NO_COLOR

    @pytest.mark.parametrize(
        "mode", [OutputMode.RAW, OutputMode.LIGHT, OutputMode.DARK]
    )
    def test_custom_output_mode_env_var(
        self, monkeypatch: pytest.MonkeyPatch, mode: OutputMode
    ) -> None:
        """Test NW_OUTPUT_MODE environment variable."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.setenv("NW_OUTPUT_MODE", mode.value)
        assert get_output_mode_from_env() is mode

    def test_default_mode_no_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default mode when no environment variables are set."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.delenv("NW_OUTPUT_MODE", raising=False)
        assert get_output_mode_from_env() is OutputMode.DEFAULT


class TestGlobalOutputManager:
    """Test global output manager functions."""

    def test_get_output_manager_singleton(self) -> None:
        """Test that get_output_manager returns the same instance."""
        # Reset global state first
        set_output_mode(OutputMode.DEFAULT)

        manager1 = get_output_manager()
        manager2 = get_output_manager()

        # Should be the same instance
        assert manager1 is manager2

    def test_set_output_mode_changes_global(self) -> None:
        """Test that set_output_mode changes the global manager."""
        # Set to raw mode
        manager = set_output_mode(OutputMode.RAW)
        assert manager.mode == OutputMode.RAW

        # Get the global manager
        global_manager = get_output_manager()
        assert global_manager.mode == OutputMode.RAW

        # Reset to normal for other tests
        set_output_mode(OutputMode.DEFAULT)

    def test_convenience_functions(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Convenience functions write through the current output manager."""
        from network_toolkit.common.output import (
            print_device_output,
            print_error,
            print_info,
            print_success,
            print_warning,
        )

        set_output_mode(OutputMode.NO_COLOR)
        print_success("Test success")
        print_error("Test error")
        print_warning("Test warning")
        print_info("Test info")
        print_device_output("sw-acc1", "test command", "test output")
        set_output_mode(OutputMode.DEFAULT)

        output = capsys.readouterr().out
        for message in (
            "Test success",
            "Test error",
            "Test warning",
            "Test info",
            "test output",
        ):
            assert message in output


class TestOutputManagerThemes:
    """Test output manager theme functionality."""

    @pytest.mark.parametrize(
        "mode", [OutputMode.DEFAULT, OutputMode.LIGHT, OutputMode.DARK]
    )
    def test_themes_render_styled_output(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        mode: OutputMode,
    ) -> None:
        """Themed modes render semantic styles when color is forced."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("NW_OUTPUT_MODE", mode.value)
        monkeypatch.setenv("TERM", "xterm-256color")
        manager = OutputManager(get_output_mode_from_env())

        manager.print_error("Test error message")
        manager.print_warning("Test warning message")
        manager.print_success("Test success message")

        assert manager.mode is mode
        lines = capsys.readouterr().out.splitlines()
        for line, label, message in zip(
            lines,
            ["FAIL", "WARN", "OK"],
            ["Test error message", "Test warning message", "Test success message"],
            strict=True,
        ):
            assert "\x1b[" in line
            assert label in line
            assert message in line

    def test_normal_mode_basic_output(self) -> None:
        """Test normal mode console output works."""
        manager = OutputManager(OutputMode.DEFAULT)
        console = manager.console

        # Normal mode should handle basic rich markup
        console.print("[bold]Test bold text[/bold]")
        console.print("[red]Test red text[/red]")

    def test_raw_mode_no_color_system(self) -> None:
        """Test raw mode has no color system."""
        manager = OutputManager(OutputMode.RAW)
        # Raw mode console should not have color system
        assert manager.console.color_system is None

    def test_no_color_mode_no_color_system(self) -> None:
        """Test no-color mode has no color system."""
        manager = OutputManager(OutputMode.NO_COLOR)
        # No-color mode should disable color system
        assert manager.console.color_system is None


class TestOutputManagerUtilityMethods:
    """Test OutputManager utility methods."""

    def test_print_transport_info_normal_mode(self, capsys: Any) -> None:
        """Test transport info printing in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        manager.print_transport_info("scrapli")

        captured = capsys.readouterr()
        assert "Transport:" in captured.out
        assert "scrapli" in captured.out

    def test_print_transport_info_raw_mode(self, capsys: Any) -> None:
        """Test transport info printing in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        manager.print_transport_info("scrapli")

        captured = capsys.readouterr()
        assert captured.out == "transport=scrapli\n"

    def test_print_running_command_normal_mode(self, capsys: Any) -> None:
        """Test running command printing in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        manager.print_running_command("/system/clock/print")

        captured = capsys.readouterr()
        assert "Running:" in captured.out
        # Check that the command parts are present (Rich may split it with formatting)
        assert "system" in captured.out
        assert "clock" in captured.out
        assert "print" in captured.out

    def test_print_running_command_raw_mode(self, capsys: Any) -> None:
        """Test running command printing in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        manager.print_running_command("/system/clock/print")

        captured = capsys.readouterr()
        assert captured.out == "running=/system/clock/print\n"

    def test_print_connection_status_connected_normal(self, capsys: Any) -> None:
        """Test connection status (connected) in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        manager.print_connection_status("sw-acc1", True)

        captured = capsys.readouterr()
        assert "OK" in captured.out
        assert "Connected" in captured.out
        assert "sw-acc1" in captured.out

    def test_print_connection_status_failed_normal(self, capsys: Any) -> None:
        """Test connection status (failed) in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        manager.print_connection_status("sw-acc1", False)

        captured = capsys.readouterr()
        assert "FAIL" in captured.out
        assert "Failed" in captured.out
        assert "sw-acc1" in captured.out

    def test_print_connection_status_raw_mode(self, capsys: Any) -> None:
        """Test connection status in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        manager.print_connection_status("sw-acc1", True)

        captured = capsys.readouterr()
        assert captured.out == "device=sw-acc1 status=connected\n"

        manager.print_connection_status("sw-acc2", False)
        captured = capsys.readouterr()
        assert captured.out == "device=sw-acc2 status=failed\n"

    def test_print_downloading_normal_mode(self, capsys: Any) -> None:
        """Test downloading message in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        manager.print_downloading("sw-acc1", "config.backup")

        captured = capsys.readouterr()
        assert "Downloading" in captured.out
        assert "config.backup" in captured.out
        assert "sw-acc1" in captured.out

    def test_print_downloading_raw_mode(self, capsys: Any) -> None:
        """Test downloading message in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        manager.print_downloading("sw-acc1", "config.backup")

        captured = capsys.readouterr()
        assert captured.out == "device=sw-acc1 downloading=config.backup\n"

    def test_print_credential_info_normal_mode(self, capsys: Any) -> None:
        """Test credential info message in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        manager.print_credential_info("Will use username: admin")

        captured = capsys.readouterr()
        assert "Will use username: admin" in captured.out

    def test_print_credential_info_raw_mode(self, capsys: Any) -> None:
        """Test credential info message in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        manager.print_credential_info("Will use username: admin")

        captured = capsys.readouterr()
        assert captured.out == "credential: Will use username: admin\n"

    def test_print_unknown_warning_normal_mode(self, capsys: Any) -> None:
        """Test unknown targets warning in normal mode."""
        manager = OutputManager(OutputMode.DEFAULT)
        manager.print_unknown_warning(["unknown1", "unknown2"])

        captured = capsys.readouterr()
        assert "Unknown targets" in captured.out
        assert "unknown1" in captured.out
        assert "unknown2" in captured.out

    def test_print_unknown_warning_raw_mode(self, capsys: Any) -> None:
        """Test unknown targets warning in raw mode."""
        manager = OutputManager(OutputMode.RAW)
        manager.print_unknown_warning(["unknown1", "unknown2"])

        captured = capsys.readouterr()
        assert captured.out == "warning: unknown targets: unknown1, unknown2\n"


class TestOutputModeResolutionOrder:
    """Test resolution of output mode from environment and config."""

    def test_env_overrides_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variable NW_OUTPUT_MODE should override config setting."""
        from network_toolkit.common.output import get_output_manager_with_config

        # Ensure clean global state
        set_output_mode(OutputMode.DEFAULT)

        # Set config to light, env to dark
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.setenv("NW_OUTPUT_MODE", "dark")

        manager = get_output_manager_with_config("light")
        assert manager.mode == OutputMode.DARK

    def test_no_color_forces_no_color(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NO_COLOR forces OutputMode.NO_COLOR regardless of config/env."""
        from network_toolkit.common.output import get_output_manager_with_config

        set_output_mode(OutputMode.DEFAULT)
        monkeypatch.setenv("NW_OUTPUT_MODE", "dark")
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("FORCE_COLOR", "1")

        manager = get_output_manager_with_config("light")
        assert manager.mode == OutputMode.NO_COLOR

    def test_config_used_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Config value should be used when no env var is set."""
        from network_toolkit.common.output import get_output_manager_with_config

        set_output_mode(OutputMode.DEFAULT)
        monkeypatch.delenv("NW_OUTPUT_MODE", raising=False)
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)

        manager = get_output_manager_with_config("raw")
        assert manager.mode == OutputMode.RAW
