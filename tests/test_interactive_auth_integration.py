"""Interactive authentication through the CLI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from rich.text import Text
from typer import BadParameter
from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.common.credentials import InteractiveCredentials


class TestInteractiveAuthIntegration:
    @pytest.mark.parametrize("flag", ["--interactive-auth", "-i"])
    def test_info_command_with_interactive_auth(
        self, config_file: Path, flag: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("NW_SHOW_PLAINTEXT_PASSWORDS", raising=False)
        with patch(
            "network_toolkit.commands.info.prompt_for_credentials",
            return_value=InteractiveCredentials("prompt-user", "prompt-secret"),
        ) as prompt:
            result = CliRunner().invoke(
                app, ["info", "test_device1", "--config", str(config_file), flag]
            )

        assert result.exit_code == 0, result.output
        assert "Will use username: prompt-user" in result.output
        assert "interactive input" in result.output
        assert "prompt-secret" not in result.output
        prompt.assert_called_once_with(
            "Enter username for devices", "Enter password for devices", "admin"
        )

    def test_run_command_with_interactive_auth(self, config_file: Path) -> None:
        command = "/system/identity/print"
        with (
            patch(
                "network_toolkit.commands.run.prompt_for_credentials",
                return_value=InteractiveCredentials("prompt-user", "prompt-secret"),
            ) as prompt,
            patch("network_toolkit.device.DeviceSession") as session,
        ):
            connected_session = session.return_value.__enter__.return_value
            connected_session.execute_command.return_value = "identity: router"
            result = CliRunner().invoke(
                app,
                [
                    "run",
                    "test_device1",
                    command,
                    "--config",
                    str(config_file),
                    "--interactive-auth",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "identity: router" in result.output
        assert "prompt-secret" not in result.output
        prompt.assert_called_once()
        session.assert_called_once()
        assert session.call_args.args[2:4] == ("prompt-user", "prompt-secret")
        connected_session.execute_command.assert_called_once_with(command)

    def test_interactive_auth_help_text(self) -> None:
        result = CliRunner().invoke(app, ["info", "--help"])

        assert result.exit_code == 0, result.output
        help_text = Text.from_ansi(result.output).plain
        assert "--interactive-auth" in help_text
        assert "Prompt for username and password interactively" in help_text


class TestInteractiveAuthErrorHandling:
    def test_keyboard_interrupt_handling(self, config_file: Path) -> None:
        with patch(
            "network_toolkit.commands.info.prompt_for_credentials",
            side_effect=KeyboardInterrupt,
        ) as prompt:
            result = CliRunner().invoke(
                app, ["info", "test_device1", "--config", str(config_file), "-i"]
            )

        assert result.exit_code == 130, result.output
        assert "Interactive authentication mode enabled" in result.output
        prompt.assert_called_once()

    def test_empty_credentials_error(self, config_file: Path) -> None:
        with patch(
            "network_toolkit.commands.info.prompt_for_credentials",
            side_effect=BadParameter("Username cannot be empty"),
        ) as prompt:
            result = CliRunner().invoke(
                app, ["info", "test_device1", "--config", str(config_file), "-i"]
            )

        assert result.exit_code == 1, result.output
        assert "Username cannot be empty" in result.output
        prompt.assert_called_once()
