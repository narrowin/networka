"""
Tests for the interactive credentials module.

This module tests the secure credential input functionality including
prompting, validation, and integration with the authentication system.
"""

from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.common.credentials import (
    InteractiveCredentials,
    confirm_credentials,
    prompt_for_credentials,
)


class TestInteractiveCredentials:
    """Test the InteractiveCredentials namedtuple."""

    def test_interactive_credentials_creation(self) -> None:
        """Test creating InteractiveCredentials instance."""
        creds = InteractiveCredentials(username="testuser", password="testpass")

        assert creds.username == "testuser"
        assert creds.password == "testpass"

    def test_interactive_credentials_immutable(self) -> None:
        """Test that InteractiveCredentials is immutable."""
        creds = InteractiveCredentials(username="testuser", password="testpass")

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            creds.username = "newuser"  # type: ignore

        with pytest.raises(AttributeError):
            creds.password = "newpass"  # type: ignore

    def test_interactive_credentials_equality(self) -> None:
        """Test InteractiveCredentials equality comparison."""
        creds1 = InteractiveCredentials(username="testuser", password="testpass")
        creds2 = InteractiveCredentials(username="testuser", password="testpass")
        creds3 = InteractiveCredentials(username="different", password="testpass")

        assert creds1 == creds2
        assert creds1 != creds3


class TestPromptForCredentials:
    """Test the prompt_for_credentials function."""

    @patch("typer.prompt")
    @patch("getpass.getpass")
    def test_prompt_for_credentials_basic(
        self, mock_getpass: MagicMock, mock_prompt: MagicMock
    ) -> None:
        """Test basic credential prompting."""
        mock_prompt.return_value = "testuser"
        mock_getpass.return_value = "testpass"

        creds = prompt_for_credentials("Enter username", "Enter password")

        assert creds.username == "testuser"
        assert creds.password == "testpass"
        mock_prompt.assert_called_once_with("Enter username")
        mock_getpass.assert_called_once_with("Enter password: ")

    @patch("typer.prompt")
    @patch("getpass.getpass")
    def test_prompt_for_credentials_with_default(
        self, mock_getpass: MagicMock, mock_prompt: MagicMock
    ) -> None:
        """Test credential prompting with default username."""
        mock_prompt.return_value = "customuser"
        mock_getpass.return_value = "testpass"

        creds = prompt_for_credentials(
            "Enter username", "Enter password", default_username="admin"
        )

        assert creds.username == "customuser"
        assert creds.password == "testpass"
        mock_prompt.assert_called_once_with(
            "Enter username [admin]", default="admin", show_default=False
        )
        mock_getpass.assert_called_once_with("Enter password: ")

    @patch("typer.prompt")
    @patch("getpass.getpass")
    def test_prompt_for_credentials_empty_username_error(
        self, mock_getpass: MagicMock, mock_prompt: MagicMock
    ) -> None:
        """Test credential prompting with empty username raises error."""
        mock_prompt.return_value = "   "  # Whitespace only
        mock_getpass.return_value = "testpass"

        with pytest.raises(Exception):
            prompt_for_credentials("Enter username", "Enter password")

    @patch("typer.prompt")
    @patch("getpass.getpass")
    def test_prompt_for_credentials_empty_password_error(
        self, mock_getpass: MagicMock, mock_prompt: MagicMock
    ) -> None:
        """Test credential prompting with empty password raises error."""
        mock_prompt.return_value = "testuser"
        mock_getpass.return_value = ""  # Empty password

        with pytest.raises(Exception):
            prompt_for_credentials("Enter username", "Enter password")

    @patch("typer.prompt")
    def test_prompt_for_credentials_keyboard_interrupt(
        self, mock_prompt: MagicMock
    ) -> None:
        """Test that KeyboardInterrupt is properly raised."""
        mock_prompt.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            prompt_for_credentials("Enter username", "Enter password")


class TestConfirmCredentials:
    """Test the confirm_credentials function."""

    @patch("typer.confirm")
    def test_confirm_credentials_accepted(self, mock_confirm: MagicMock) -> None:
        """Test credential confirmation when user accepts."""
        mock_confirm.return_value = True

        creds = InteractiveCredentials(username="testuser", password="testpass")
        result = confirm_credentials(creds)

        assert result is True
        mock_confirm.assert_called_once_with(
            "Use username 'testuser' with provided password?"
        )

    @patch("typer.confirm")
    def test_confirm_credentials_rejected(self, mock_confirm: MagicMock) -> None:
        """Test credential confirmation when user rejects."""
        mock_confirm.return_value = False

        creds = InteractiveCredentials(username="testuser", password="testpass")
        result = confirm_credentials(creds)

        assert result is False
        mock_confirm.assert_called_once_with(
            "Use username 'testuser' with provided password?"
        )

    @patch("typer.confirm")
    def test_confirm_credentials_keyboard_interrupt(
        self, mock_confirm: MagicMock
    ) -> None:
        """Test that KeyboardInterrupt is properly raised during confirmation."""
        mock_confirm.side_effect = KeyboardInterrupt()

        creds = InteractiveCredentials(username="testuser", password="testpass")

        with pytest.raises(KeyboardInterrupt):
            confirm_credentials(creds)


class TestCredentialsIntegration:
    """Test integration scenarios for the credentials module."""

    @patch("typer.prompt")
    @patch("getpass.getpass")
    @patch("typer.confirm")
    def test_full_credential_flow(
        self, mock_confirm: MagicMock, mock_getpass: MagicMock, mock_prompt: MagicMock
    ) -> None:
        """Test the complete credential prompting and confirmation flow."""
        mock_prompt.return_value = "admin"
        mock_getpass.return_value = "secret123"
        mock_confirm.return_value = True

        # Simulate full flow
        creds = prompt_for_credentials(
            "Enter username for devices",
            "Enter password for devices",
            default_username="admin",
        )

        confirmed = confirm_credentials(creds)

        assert creds.username == "admin"
        assert creds.password == "secret123"
        assert confirmed is True

    @patch("typer.prompt")
    @patch("getpass.getpass")
    @patch("typer.confirm")
    def test_credential_flow_rejected(
        self, mock_confirm: MagicMock, mock_getpass: MagicMock, mock_prompt: MagicMock
    ) -> None:
        """Test credential flow when user rejects confirmation."""
        mock_prompt.return_value = "admin"
        mock_getpass.return_value = "secret123"
        mock_confirm.return_value = False

        creds = prompt_for_credentials(
            "Enter username for devices", "Enter password for devices"
        )

        confirmed = confirm_credentials(creds)

        assert creds.username == "admin"
        assert creds.password == "secret123"
        assert confirmed is False

    def test_credentials_string_representation(self) -> None:
        """Test string representations don't expose password."""
        creds = InteractiveCredentials(username="testuser", password="secret123")

        # Check repr and str don't contain password
        repr_str = repr(creds)
        str_repr = str(creds)

        assert "testuser" in repr_str
        assert "testuser" in str_repr
        # Password should be present in the actual data structure
        assert creds.password == "secret123"
