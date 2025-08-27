"""Test for SmartConsole and output formatting."""

from __future__ import annotations

from unittest.mock import patch

from network_toolkit.common.output_clean import (
    OutputMode,
    SmartConsole,
    create_smart_console,
    format_output,
)


class TestSmartConsole:
    """Test SmartConsole functionality."""

    def test_smart_console_rich_mode(self):
        """Test SmartConsole in rich mode."""
        console = SmartConsole(OutputMode.RICH)
        assert console.mode == OutputMode.RICH

    def test_smart_console_no_color_mode(self):
        """Test SmartConsole in no-color mode."""
        console = SmartConsole(OutputMode.NO_COLOR)
        assert console.mode == OutputMode.NO_COLOR

    @patch("builtins.print")
    def test_smart_console_no_color_print(self, mock_print):
        """Test SmartConsole print in no-color mode."""
        console = SmartConsole(OutputMode.NO_COLOR)
        console.print("Test message")
        mock_print.assert_called_once_with("Test message")

    @patch("builtins.print")
    def test_smart_console_no_color_print_with_markup(self, mock_print):
        """Test SmartConsole strips markup in no-color mode."""
        console = SmartConsole(OutputMode.NO_COLOR)
        console.print("[red]Error message[/red]")
        mock_print.assert_called_once_with("Error message")

    def test_smart_console_rich_print(self):
        """Test SmartConsole print in rich mode."""
        console = SmartConsole(OutputMode.RICH)
        with patch.object(console, "_rich_console") as mock_rich:
            console.print("Test message", "blue")
            # Verify function was called and contains expected content (not specific markup)
            mock_rich.print.assert_called_once()
            call_arg = mock_rich.print.call_args[0][0]
            assert "Test message" in call_arg

    @patch("builtins.print")
    def test_smart_console_print_warning_no_color(self, mock_print):
        """Test print_warning in no-color mode."""
        console = SmartConsole(OutputMode.NO_COLOR)
        console.print_warning("Warning message")
        mock_print.assert_called_once_with("Warning message")

    @patch("builtins.print")
    def test_smart_console_print_error_no_color(self, mock_print):
        """Test print_error in no-color mode."""
        console = SmartConsole(OutputMode.NO_COLOR)
        console.print_error("Error occurred")
        mock_print.assert_called_once_with("FAIL Error occurred")

    def test_create_smart_console(self):
        """Test create_smart_console factory function."""
        console = create_smart_console(OutputMode.NO_COLOR)
        assert isinstance(console, SmartConsole)
        assert console.mode == OutputMode.NO_COLOR


class TestFormatOutput:
    """Test format_output function."""

    def test_format_output_json(self):
        """Test JSON output format."""
        data = [{"name": "device1", "host": "192.168.1.1"}]
        headers = ["Name", "Host"]
        result = format_output(data, headers, "Test", OutputMode.JSON)
        assert '"name": "device1"' in result
        assert '"host": "192.168.1.1"' in result

    def test_format_output_csv(self):
        """Test CSV output format."""
        data = [{"name": "device1", "host": "192.168.1.1"}]
        headers = ["name", "host"]
        result = format_output(data, headers, "Test", OutputMode.CSV)
        assert "name,host" in result
        assert "device1,192.168.1.1" in result

    def test_format_output_no_color(self):
        """Test no-color text output format."""
        data = [{"name": "device1", "host": "192.168.1.1"}]
        headers = ["Name", "Host"]
        result = format_output(data, headers, "Test Devices", OutputMode.NO_COLOR)
        assert "Test Devices" in result
        assert "Name" in result
        assert "Host" in result
        assert "device1" in result
        assert "192.168.1.1" in result
        assert "|" in result  # Table separator

    def test_format_output_no_color_empty_data(self):
        """Test no-color format with empty data."""
        data = []
        headers = ["Name", "Host"]
        result = format_output(data, headers, "Test", OutputMode.NO_COLOR)
        assert "Test" in result
        assert "No data available" in result

    def test_format_output_rich(self):
        """Test Rich table output format."""
        data = [{"name": "device1", "host": "192.168.1.1"}]
        headers = ["Name", "Host"]
        styles = {"name": "device", "host": "cyan"}
        result = format_output(data, headers, "Test", OutputMode.RICH, styles)

        # Should return a Rich Table object
        from rich.table import Table

        assert isinstance(result, Table)

    def test_format_output_rich_with_unknown_style(self):
        """Test Rich format handles unknown styles gracefully."""
        data = [{"name": "device1", "host": "192.168.1.1"}]
        headers = ["Name", "Host"]
        styles = {"name": "unknown_style", "host": "cyan"}

        # Should not raise an error
        result = format_output(data, headers, "Test", OutputMode.RICH, styles)
        from rich.table import Table

        assert isinstance(result, Table)


class TestOutputModeDetection:
    """Test output mode detection from environment."""

    @patch.dict("os.environ", {"NO_COLOR": "1"})
    def test_no_color_env_detection(self):
        """Test NO_COLOR environment variable detection."""
        from network_toolkit.common.output_clean import get_output_mode_from_env

        assert get_output_mode_from_env() == OutputMode.NO_COLOR

    @patch.dict("os.environ", {"FORCE_COLOR": "1"})
    def test_force_color_env_detection(self):
        """Test FORCE_COLOR environment variable detection."""
        from network_toolkit.common.output_clean import get_output_mode_from_env

        assert get_output_mode_from_env() == OutputMode.RICH

    @patch.dict("os.environ", {"CI": "true"})
    def test_ci_env_detection(self):
        """Test CI environment detection."""
        from network_toolkit.common.output_clean import get_output_mode_from_env

        assert get_output_mode_from_env() == OutputMode.NO_COLOR

    @patch.dict("os.environ", {}, clear=True)
    def test_default_mode_detection(self):
        """Test default mode when no env vars set."""
        from network_toolkit.common.output_clean import get_output_mode_from_env

        assert get_output_mode_from_env() == OutputMode.RICH
        assert get_output_mode_from_env() == OutputMode.RICH
        assert get_output_mode_from_env() == OutputMode.RICH
