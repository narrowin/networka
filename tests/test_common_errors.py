"""Tests for common.errors module."""

from unittest.mock import MagicMock

from rich.console import Console

from network_toolkit.common.errors import (
    format_error_message,
    print_error,
    print_success,
    print_warning,
)


class TestErrorFormatting:
    """Test error formatting functions."""

    def test_format_error_message_basic(self) -> None:
        """Test basic error message formatting."""
        result = format_error_message("Connection failed")
        assert result == "Connection failed"

    def test_format_error_message_with_context(self) -> None:
        """Test error message formatting with context."""
        result = format_error_message("Connection failed", context="device1")
        assert result == "[device1] Connection failed"

    def test_format_error_message_with_details(self) -> None:
        """Test error message formatting with details."""
        details = {"host": "192.168.1.1", "port": 22}
        result = format_error_message("Connection failed", details=details)
        assert result == "Connection failed (host=192.168.1.1, port=22)"

    def test_format_error_message_with_context_and_details(self) -> None:
        """Test error message formatting with both context and details."""
        details = {"timeout": 30}
        result = format_error_message(
            "Connection failed", details=details, context="device1"
        )
        assert result == "[device1] Connection failed (timeout=30)"

    def test_print_error(self) -> None:
        """Test print_error function."""
        console = MagicMock(spec=Console)

        print_error(console, "Test error")

        console.print.assert_called_once_with("[red]Error: Test error[/red]")

    def test_print_error_with_context(self) -> None:
        """Test print_error function with context."""
        console = MagicMock(spec=Console)

        print_error(console, "Test error", context="device1")

        console.print.assert_called_once_with("[red]Error: [device1] Test error[/red]")

    def test_print_error_with_details(self) -> None:
        """Test print_error function with details."""
        console = MagicMock(spec=Console)
        details = {"host": "192.168.1.1"}

        print_error(console, "Test error", details=details)

        console.print.assert_called_once_with(
            "[red]Error: Test error (host=192.168.1.1)[/red]"
        )

    def test_print_warning(self) -> None:
        """Test print_warning function."""
        console = MagicMock(spec=Console)

        print_warning(console, "Test warning")

        console.print.assert_called_once_with("[yellow]Warning: Test warning[/yellow]")

    def test_print_warning_with_context(self) -> None:
        """Test print_warning function with context."""
        console = MagicMock(spec=Console)

        print_warning(console, "Test warning", context="device1")

        console.print.assert_called_once_with(
            "[yellow]Warning: [device1] Test warning[/yellow]"
        )

    def test_print_warning_with_details(self) -> None:
        """Test print_warning function with details."""
        console = MagicMock(spec=Console)
        details = {"timeout": 30}

        print_warning(console, "Test warning", details=details)

        console.print.assert_called_once_with(
            "[yellow]Warning: Test warning (timeout=30)[/yellow]"
        )

    def test_print_success(self) -> None:
        """Test print_success function."""
        console = MagicMock(spec=Console)

        print_success(console, "Test success")

        console.print.assert_called_once_with("[green]Test success[/green]")

    def test_print_success_with_context(self) -> None:
        """Test print_success function with context."""
        console = MagicMock(spec=Console)

        print_success(console, "Test success", context="device1")

        console.print.assert_called_once_with("[green][device1] Test success[/green]")

    def test_print_success_with_details(self) -> None:
        """Test print_success function with details."""
        console = MagicMock(spec=Console)
        details = {"files": 3}

        print_success(console, "Test success", details=details)

        console.print.assert_called_once_with("[green]Test success (files=3)[/green]")

    def test_format_error_message_empty_details(self) -> None:
        """Test error message formatting with empty details."""
        result = format_error_message("Test error", details={})
        assert result == "Test error"

    def test_format_error_message_none_values(self) -> None:
        """Test error message formatting with None values."""
        result = format_error_message("Test error", details=None, context=None)
        assert result == "Test error"

    def test_print_error_with_all_parameters(self) -> None:
        """Test print_error with all parameters."""
        console = MagicMock(spec=Console)
        details = {"host": "192.168.1.1", "port": 22}

        print_error(console, "Connection failed", details=details, context="device1")

        expected_message = (
            "[red]Error: [device1] Connection failed (host=192.168.1.1, port=22)[/red]"
        )
        console.print.assert_called_once_with(expected_message)

    def test_print_warning_with_all_parameters(self) -> None:
        """Test print_warning with all parameters."""
        console = MagicMock(spec=Console)
        details = {"retry": 3}

        print_warning(
            console, "Retrying connection", details=details, context="device1"
        )

        expected_message = (
            "[yellow]Warning: [device1] Retrying connection (retry=3)[/yellow]"
        )
        console.print.assert_called_once_with(expected_message)

    def test_print_success_with_all_parameters(self) -> None:
        """Test print_success with all parameters."""
        console = MagicMock(spec=Console)
        details = {"duration": "2.5s"}

        print_success(
            console, "Operation completed", details=details, context="device1"
        )

        expected_message = (
            "[green][device1] Operation completed (duration=2.5s)[/green]"
        )
        console.print.assert_called_once_with(expected_message)
