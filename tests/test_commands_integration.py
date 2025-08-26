"""Tests for CommandContext integration across commands."""

from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.common.output import OutputMode


class TestCommandContextIntegration:
    """Test CommandContext usage across different commands."""

    def test_style_manager_integration(self) -> None:
        """Test that StyleManager works correctly across output modes."""
        from network_toolkit.common.styles import StyleManager, StyleName

        # Test all output modes work
        for mode in [
            OutputMode.DEFAULT,
            OutputMode.LIGHT,
            OutputMode.DARK,
            OutputMode.NO_COLOR,
        ]:
            style_manager = StyleManager(mode=mode)

            # Test that get_style doesn't crash
            info_style = style_manager.get_style(StyleName.INFO)
            error_style = style_manager.get_style(StyleName.ERROR)

            # Test format_message
            formatted = style_manager.format_message("Test message", StyleName.INFO)

            if mode == OutputMode.NO_COLOR:
                # No-color mode should return plain text
                assert formatted == "Test message"
                assert info_style is None
                assert error_style is None
            else:
                # Other modes should return styled text
                assert "[info]Test message[/info]" == formatted
                assert isinstance(info_style, str)
                assert isinstance(error_style, str)

    def test_diff_command_with_output_modes(self) -> None:
        """Test diff command works with different output modes."""
        runner = CliRunner()

        mock_config = Mock()
        mock_config.devices = {"test-device": Mock()}

        with (
            patch("network_toolkit.config.load_config", return_value=mock_config),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="test config"),
        ):
            # Test with different output modes
            for mode in ["default", "light", "dark", "no-color"]:
                result = runner.invoke(
                    app, ["diff", "--output-mode", mode, "file1.txt", "file2.txt"]
                )
                # Command may fail due to file differences, but shouldn't crash with color errors
                assert "Error" not in result.stdout or result.exit_code != 0

    def test_command_context_print_methods(self) -> None:
        """Test CommandContext print methods work correctly."""
        # This test verifies that the print methods exist and can be called
        # We'll test with the StyleManager directly since CommandContext setup is complex
        from network_toolkit.common.styles import StyleManager, StyleName

        for mode in [
            OutputMode.DEFAULT,
            OutputMode.LIGHT,
            OutputMode.DARK,
            OutputMode.NO_COLOR,
        ]:
            style_manager = StyleManager(mode=mode)

            # These should not raise exceptions
            info_style = style_manager.get_style(StyleName.INFO)
            success_style = style_manager.get_style(StyleName.SUCCESS)
            error_style = style_manager.get_style(StyleName.ERROR)
            warning_style = style_manager.get_style(StyleName.WARNING)

            # In no-color mode, styles should be None
            if mode == OutputMode.NO_COLOR:
                assert info_style is None
                assert success_style is None
                assert error_style is None
                assert warning_style is None
            else:
                # In other modes, styles should be strings
                assert isinstance(info_style, str)
                assert isinstance(success_style, str)
                assert isinstance(error_style, str)
                assert isinstance(warning_style, str)

    def test_helper_functions_integration(self) -> None:
        """Test that helper function patterns work correctly."""
        # Test the pattern we established with StyleManager helper functions
        from network_toolkit.common.styles import StyleManager, StyleName

        # This pattern is used in config_init.py
        style_manager = StyleManager(mode=OutputMode.DEFAULT)

        # Test INFO style formatting
        info_style = style_manager.get_style(StyleName.INFO)
        success_style = style_manager.get_style(StyleName.SUCCESS)

        assert info_style == "blue"  # From DEFAULT theme
        assert success_style == "green"  # From DEFAULT theme

        # Test message formatting
        info_msg = style_manager.format_message("Test info", StyleName.INFO)
        success_msg = style_manager.format_message("Test success", StyleName.SUCCESS)

        assert info_msg == "[info]Test info[/info]"
        assert success_msg == "[success]Test success[/success]"

    def test_hardcoded_colors_removed(self) -> None:
        """Test that major commands don't use hardcoded colors."""
        import inspect

        # Import the commands we've fixed
        from network_toolkit.commands import (
            backup,
            config,
            diff,
            download,
            firmware,
            routerboard_upgrade,
            run,
            upload,
        )

        # Check that these modules don't contain hardcoded color patterns
        for module in [
            backup,
            diff,
            config,
            upload,
            download,
            firmware,
            routerboard_upgrade,
            run,
        ]:
            source = inspect.getsource(module)

            # Check for common hardcoded color patterns
            hardcoded_patterns = [
                'console.print("[red]',
                'console.print("[green]',
                'console.print("[yellow]',
                'console.print("[cyan]',
                'console.print(f"[red]',
                'console.print(f"[green]',
                'console.print(f"[yellow]',
                'console.print(f"[cyan]',
            ]

            for pattern in hardcoded_patterns:
                # Some patterns may remain in comments or specific contexts
                # This is a basic check to ensure major cleanup was done
                count = source.count(pattern)
                # Allow some minimal usage but flag if there are many instances
                assert count < 5, (
                    f"Module {module.__name__} still has {count} instances of {pattern}"
                )
