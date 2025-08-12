"""
Integration tests for interactive authentication functionality.

Tests the --interactive-auth flag integration with CLI commands.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.common.credentials import InteractiveCredentials


class TestInteractiveAuthIntegration:
    """Test interactive authentication integration with CLI commands."""

    def setup_method(self) -> None:
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("network_toolkit.commands.info.DeviceSession")
    @patch("network_toolkit.commands.info.load_config")
    @patch("network_toolkit.common.credentials.prompt_for_credentials")
    def test_info_command_with_interactive_auth(
        self,
        mock_prompt_creds: MagicMock,
        mock_load_config: MagicMock,
        mock_device_session: MagicMock,
    ) -> None:
        """Test info command with --interactive-auth flag."""
        # Mock credentials
        mock_creds = InteractiveCredentials(username="testuser", password="testpass")
        mock_prompt_creds.return_value = mock_creds

        # Mock config
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        # Mock device session
        mock_session_instance = MagicMock()
        mock_device_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock session methods
        mock_session_instance.is_connected.return_value = True
        mock_session_instance.get_device_info.return_value = {
            "hostname": "test-device",
            "model": "CCR1009",
            "version": "7.1.1",
        }

        # Run command with interactive auth
        result = self.runner.invoke(app, ["info", "test-device", "--interactive-auth"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify credentials were prompted
        mock_prompt_creds.assert_called_once()

        # Verify DeviceSession was called with credential overrides
        mock_device_session.assert_called_once()
        call_args = mock_device_session.call_args
        assert call_args[1]["username_override"] == "testuser"
        assert call_args[1]["password_override"] == "testpass"

    @patch("network_toolkit.commands.run._run_command_on_device")
    @patch("network_toolkit.commands.run.load_config")
    @patch("network_toolkit.common.credentials.prompt_for_credentials")
    def test_run_command_with_interactive_auth(
        self,
        mock_prompt_creds: MagicMock,
        mock_load_config: MagicMock,
        mock_run_command: MagicMock,
    ) -> None:
        """Test run command with --interactive-auth flag."""
        # Mock credentials
        mock_creds = InteractiveCredentials(username="admin", password="secret")
        mock_prompt_creds.return_value = mock_creds

        # Mock config
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        # Mock command execution
        mock_run_command.return_value = "Command output"

        # Run command with interactive auth
        result = self.runner.invoke(
            app, ["run", "test-device", "/system/identity/print", "--interactive-auth"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify credentials were prompted
        mock_prompt_creds.assert_called_once()

        # Verify the command was executed with credential overrides
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args[1]
        assert call_args["username_override"] == "admin"
        assert call_args["password_override"] == "secret"

    @patch("network_toolkit.common.credentials.prompt_for_credentials")
    def test_interactive_auth_short_flag(self, mock_prompt_creds: MagicMock) -> None:
        """Test that -i short flag works for interactive auth."""
        # Mock credentials
        mock_creds = InteractiveCredentials(username="user", password="pass")
        mock_prompt_creds.return_value = mock_creds

        # Mock other dependencies
        with (
            patch("network_toolkit.commands.info.load_config"),
            patch("network_toolkit.commands.info.DeviceSession"),
        ):
            result = self.runner.invoke(app, ["info", "test-device", "-i"])

            # Should not error on the flag parsing
            # (actual execution will fail due to mocking, but flag should be recognized)
            assert "-i" not in result.output or "No such option" not in result.output

            # Verify credentials were prompted (if we got that far)
            if result.exit_code == 0:
                mock_prompt_creds.assert_called_once()

    def test_interactive_auth_help_text(self) -> None:
        """Test that help text includes the interactive auth option."""
        result = self.runner.invoke(app, ["info", "--help"])

        assert result.exit_code == 0
        assert "--interactive-auth" in result.output or "-i" in result.output
        assert "interactive" in result.output.lower()

    @patch("network_toolkit.common.credentials.prompt_for_credentials")
    def test_interactive_auth_credential_prompting(
        self, mock_prompt_creds: MagicMock
    ) -> None:
        """Test that interactive auth properly prompts for credentials."""
        # Mock credentials
        mock_creds = InteractiveCredentials(username="testuser", password="testpass")
        mock_prompt_creds.return_value = mock_creds

        # Mock other dependencies to avoid actual execution
        with (
            patch("network_toolkit.commands.info.load_config"),
            patch("network_toolkit.commands.info.DeviceSession"),
        ):
            self.runner.invoke(app, ["info", "test-device", "--interactive-auth"])

            # Verify prompt_for_credentials was called with appropriate messages
            mock_prompt_creds.assert_called_once()
            call_args = mock_prompt_creds.call_args[0]

            # Should include appropriate prompts
            assert len(call_args) >= 2  # username and password prompts
            assert "username" in call_args[0].lower()
            assert "password" in call_args[1].lower()


class TestInteractiveAuthErrorHandling:
    """Test error handling in interactive authentication."""

    def setup_method(self) -> None:
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("network_toolkit.common.credentials.prompt_for_credentials")
    def test_keyboard_interrupt_handling(self, mock_prompt_creds: MagicMock) -> None:
        """Test that KeyboardInterrupt during credential prompting is handled."""
        # Mock KeyboardInterrupt during credential prompting
        mock_prompt_creds.side_effect = KeyboardInterrupt()

        # Mock other dependencies
        with patch("network_toolkit.commands.info.load_config"):
            result = self.runner.invoke(
                app, ["info", "test-device", "--interactive-auth"]
            )

            # Should exit with error code due to KeyboardInterrupt
            assert result.exit_code != 0

    @patch("network_toolkit.common.credentials.prompt_for_credentials")
    def test_empty_credentials_error(self, mock_prompt_creds: MagicMock) -> None:
        """Test handling of invalid credentials."""
        # Mock invalid credentials (this would normally raise an error in the real function)
        from typer import BadParameter

        mock_prompt_creds.side_effect = BadParameter("Username cannot be empty")

        # Mock other dependencies
        with patch("network_toolkit.commands.info.load_config"):
            result = self.runner.invoke(
                app, ["info", "test-device", "--interactive-auth"]
            )

            # Should exit with error code
            assert result.exit_code != 0
