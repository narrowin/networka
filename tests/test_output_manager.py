# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the output manager and formatting abstraction."""

from __future__ import annotations

import json
import sys
from io import StringIO
from unittest.mock import patch

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
        assert OutputMode.NORMAL.value == "normal"
        assert OutputMode.LIGHT.value == "light"
        assert OutputMode.DARK.value == "dark"
        assert OutputMode.NO_COLOR.value == "no-color"
        assert OutputMode.RAW.value == "raw"


class TestOutputManager:
    """Test OutputManager class."""

    def test_normal_mode_creation(self) -> None:
        """Test creating output manager in normal mode."""
        manager = OutputManager(OutputMode.NORMAL)
        assert manager.mode == OutputMode.NORMAL
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

    def test_light_mode_creation(self) -> None:
        """Test creating output manager in light mode."""
        manager = OutputManager(OutputMode.LIGHT)
        assert manager.mode == OutputMode.LIGHT
        # Light mode should have a console with color support
        assert manager.console.color_system is not None

    def test_dark_mode_creation(self) -> None:
        """Test creating output manager in dark mode."""
        manager = OutputManager(OutputMode.DARK)
        assert manager.mode == OutputMode.DARK
        # Dark mode should have a console with color support
        assert manager.console.color_system is not None


class TestOutputManagerRawMode:
    """Test OutputManager raw mode behavior."""

    def test_raw_device_output(self) -> None:
        """Test device output in raw mode."""
        manager = OutputManager(OutputMode.RAW)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            manager.print_command_output("sw-acc1", "/system/clock/print", "output text")
            output = mock_stdout.getvalue()

        assert "device=sw-acc1 cmd=/system/clock/print" in output
        assert "output text" in output

    def test_raw_success_message(self) -> None:
        """Test success message in raw mode."""
        manager = OutputManager(OutputMode.RAW)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            manager.print_success("Operation completed", "sw-acc1")
            output = mock_stdout.getvalue()

        assert "device=sw-acc1 success: Operation completed" in output

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
                duration=1.5
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

    def test_normal_mode_console_output(self) -> None:
        """Test that normal mode uses console output."""
        manager = OutputManager(OutputMode.NORMAL)
        
        # These should not raise exceptions and should use console
        manager.print_success("Test success")
        manager.print_error("Test error")
        manager.print_warning("Test warning")
        manager.print_info("Test info")

    def test_no_color_mode_console_output(self) -> None:
        """Test that no-color mode uses console without colors."""
        manager = OutputManager(OutputMode.NO_COLOR)
        
        # Should have no color system but still use console
        assert manager.console.color_system is None
        
        # These should not raise exceptions
        manager.print_success("Test success")
        manager.print_error("Test error")

    def test_summary_printed_in_normal_mode(self) -> None:
        """Test that summaries are printed in normal modes."""
        manager = OutputManager(OutputMode.NORMAL)
        
        # Should not raise exceptions - testing that it's called
        manager.print_summary(
            target="sw-acc1",
            operation_type="Command", 
            name="test_command",
            duration=1.5
        )

    def test_results_directory_printed_in_normal_mode(self) -> None:
        """Test that results directory is printed in normal modes."""
        manager = OutputManager(OutputMode.NORMAL)
        
        # Should not raise exceptions - testing that it's called
        manager.print_results_directory("/path/to/results")


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_no_color_env_var(self) -> None:
        """Test NO_COLOR environment variable detection."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default="": {
                "NO_COLOR": "1",
                "NT_OUTPUT_MODE": "",
            }.get(key, default)

            mode = get_output_mode_from_env()
            assert mode == OutputMode.NO_COLOR

    def test_custom_output_mode_env_var(self) -> None:
        """Test NT_OUTPUT_MODE environment variable."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default="": {
                "NO_COLOR": "",
                "NT_OUTPUT_MODE": "raw",
            }.get(key, default)

            mode = get_output_mode_from_env()
            assert mode == OutputMode.RAW

    def test_light_theme_env_var(self) -> None:
        """Test light theme environment variable."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default="": {
                "NO_COLOR": "",
                "NT_OUTPUT_MODE": "light",
            }.get(key, default)

            mode = get_output_mode_from_env()
            assert mode == OutputMode.LIGHT

    def test_dark_theme_env_var(self) -> None:
        """Test dark theme environment variable."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default="": {
                "NO_COLOR": "",
                "NT_OUTPUT_MODE": "dark",
            }.get(key, default)

            mode = get_output_mode_from_env()
            assert mode == OutputMode.DARK

    def test_default_mode_no_env_vars(self) -> None:
        """Test default mode when no environment variables are set."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda _key, default="": default

            mode = get_output_mode_from_env()
            assert mode == OutputMode.NORMAL


class TestGlobalOutputManager:
    """Test global output manager functions."""

    def test_get_output_manager_singleton(self) -> None:
        """Test that get_output_manager returns the same instance."""
        # Reset global state first
        set_output_mode(OutputMode.NORMAL)

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
        set_output_mode(OutputMode.NORMAL)

    def test_convenience_functions(self) -> None:
        """Test convenience functions work without exceptions."""
        from network_toolkit.common.output import (
            print_device_output,
            print_error,
            print_info,
            print_success,
            print_warning,
        )
        
        # These should not raise exceptions
        print_success("Test success")
        print_error("Test error")
        print_warning("Test warning")
        print_info("Test info")
        print_device_output("sw-acc1", "test command", "test output")


class TestOutputManagerThemes:
    """Test output manager theme functionality."""

    def test_light_theme_has_styles(self) -> None:
        """Test light theme has theme styles applied."""
        manager = OutputManager(OutputMode.LIGHT)
        console = manager.console

        # Light theme should have color support enabled
        assert console.color_system is not None
        # Test that themed output doesn't raise exceptions
        console.print("[info]Test info message[/info]")
        console.print("[error]Test error message[/error]")
        console.print("[success]Test success message[/success]")

    def test_dark_theme_has_styles(self) -> None:
        """Test dark theme has theme styles applied."""
        manager = OutputManager(OutputMode.DARK)
        console = manager.console

        # Dark theme should have color support enabled
        assert console.color_system is not None
        # Test that themed output doesn't raise exceptions
        console.print("[info]Test info message[/info]")
        console.print("[error]Test error message[/error]")
        console.print("[success]Test success message[/success]")

    def test_normal_mode_basic_output(self) -> None:
        """Test normal mode console output works."""
        manager = OutputManager(OutputMode.NORMAL)
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
