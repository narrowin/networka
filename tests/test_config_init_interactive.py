# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Additional tests for config-init interactive features and options.

These tests avoid network and real home writes by mocking subprocess and paths.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import network_toolkit.commands.config_init as config_init_mod
from network_toolkit.cli import app
from network_toolkit.exceptions import FileTransferError


def test_config_init_yes_uses_default_location(monkeypatch: Any) -> None:
    """--yes with no target_dir uses default_config_root and creates files there."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Redirect default config root to a temp dir
        monkeypatch.setattr(config_init_mod, "default_config_root", lambda: tmp_path)

        result = runner.invoke(app, ["config", "init", "--yes"])  # non-interactive

        assert result.exit_code == 0
        assert (tmp_path / ".env").exists()
        assert (tmp_path / "config.yml").exists()
        assert (tmp_path / "devices" / "mikrotik.yml").exists()
        assert (tmp_path / "groups" / "main.yml").exists()
        assert (tmp_path / "sequences" / "basic.yml").exists()


def test_config_init_dry_run_interactive_no_writes(monkeypatch: Any) -> None:
    """Interactive dry-run prints actions and writes nothing."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        monkeypatch.setattr(config_init_mod, "default_config_root", lambda: tmp_path)

        # Use defaults, then answer No to sequences and No to completions
        user_input = "\n"  # accept default path (press Enter)
        user_input += "n\n"  # do not install sequences
        user_input += "n\n"  # do not install completions

        result = runner.invoke(app, ["config", "init", "--dry-run"], input=user_input)

        assert result.exit_code == 0
        # Nothing should be created in dry-run
        assert not (tmp_path / ".env").exists()
    # But the output should mention planned actions
    assert "Would create file:" in result.stdout
    assert "Would ensure directory:" in result.stdout


def test_config_init_install_sequences_triggers_git_clone(monkeypatch: Any) -> None:
    """--install-sequences should attempt a git clone, but we mock subprocess.run."""
    import shutil

    runner = CliRunner()

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))

        class _Result:
            returncode = 0
            stderr = ""

        return _Result()

    # Mock shutil.which to return a git path
    def mock_which(cmd: str) -> str | None:
        if cmd == "git":
            return "/usr/bin/git"
        return None

    # Patch the subprocess.run used inside the module under test
    monkeypatch.setattr(config_init_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", mock_which)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                str(test_dir),
                "--install-sequences",
                "--git-url",
                "https://example.invalid/repo.git",
                "--git-ref",
                "ssh_multiplex",
            ],
        )

        assert result.exit_code == 0
        # We attempted to run git clone once - check for full git path (security improvement)
        assert any(
            "/usr/bin/git" in str(args[0])
            for args, _ in calls
            if args and args[0] and len(args[0]) > 0
        )


def test_config_init_install_completions_install_and_activate(monkeypatch: Any) -> None:
    """Installing completions installs script under HOME and updates rc file."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        # Ensure a harmless HOME to avoid touching real rc files (though we skip install here)
        monkeypatch.setenv("HOME", str(test_dir))
        # Force a known shell
        monkeypatch.setenv("SHELL", "/bin/bash")

        result = runner.invoke(
            app,
            [
                "config",
                "init",
                str(test_dir),
                "--install-completions",
                "--shell",
                "bash",
                "--activate-completions",
            ],
        )

        assert result.exit_code == 0
        # Should report installation and rc update under our temp HOME
        assert "Installed bash completion script to:" in result.stdout
        assert str(test_dir) in result.stdout
        # Check for the new logging message format from our improved implementation
        assert (
            "Activation snippet appended. Open a new shell to use completions."
            in result.stdout
        )


def test_clone_error_handling() -> None:
    """Test git clone error handling in install_sequences_from_repo."""
    runner = CliRunner()

    with patch(
        "network_toolkit.commands.config_init.subprocess.run"
    ) as mock_subprocess:
        # Mock git clone failure
        mock_subprocess.side_effect = CalledProcessError(128, ["git", "clone"])

        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                app,
                [
                    "config",
                    "init",
                    temp_dir,  # target_dir positional argument
                    "--git-url",
                    "https://github.com/owner/repo.git",
                    "--install-sequences",  # Enable sequences to trigger git clone
                    "--no-install-completions",
                    "--no-install-schemas",
                    "--yes",  # Non-interactive mode
                ],
            )

            # The application should continue gracefully and show a warning
            assert result.exit_code == 0
            assert "Failed to install sequences" in result.stdout


def test_env_file_creation_error() -> None:
    """Test .env file creation error handling."""
    runner = CliRunner()

    # Mock Path.write_text to raise PermissionError when writing .env file
    with patch("pathlib.Path.write_text", side_effect=PermissionError("Access denied")):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                app,
                [
                    "config",
                    "init",
                    temp_dir,  # target_dir positional argument
                    "--no-install-sequences",
                    "--no-install-completions",
                    "--no-install-schemas",
                    "--yes",  # Non-interactive mode
                ],
            )

            assert result.exit_code == 1
            assert "Failed to create .env file" in result.stdout


def test_failed_git_clone_error_handling(monkeypatch: Any) -> None:
    """Test that failed git clone operations are handled gracefully."""
    import shutil
    import subprocess

    runner = CliRunner()

    def mock_run(*args: Any, **kwargs: Any) -> Any:
        # Simulate git clone failure
        error = subprocess.CalledProcessError(
            128, "git", stderr="fatal: repository not found"
        )
        raise error

    def mock_which(cmd: str) -> str | None:
        if cmd == "git":
            return "/usr/bin/git"
        return None

    monkeypatch.setattr(config_init_mod.subprocess, "run", mock_run)
    monkeypatch.setattr(shutil, "which", mock_which)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                str(test_dir),
                "--install-sequences",
                "--git-url",
                "https://github.com/nonexistent/repo.git",
            ],
        )

        # Should still complete successfully but show warning about sequences
        assert result.exit_code == 0
        assert "Failed to install sequences" in result.stdout


def test_completion_script_not_found(monkeypatch: Any) -> None:
    """Test behavior when completion scripts are not found."""
    runner = CliRunner()

    # Mock _detect_repo_root to return None (scripts not found)
    monkeypatch.setattr(config_init_mod, "_detect_repo_root", lambda: None)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                str(test_dir),
                "--install-completions",
                "--shell",
                "bash",
            ],
        )

        # Should still complete successfully but show warning about completions
        assert result.exit_code == 0
        assert "Shell completion installation failed" in result.stdout


def test_file_creation_error_handling(monkeypatch: Any) -> None:
    """Test that file creation errors are handled gracefully."""
    from network_toolkit.commands.config_init import create_env_file

    # Create a read-only directory to simulate permission error
    with tempfile.TemporaryDirectory() as tmpdir:
        readonly_dir = Path(tmpdir) / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        with pytest.raises(FileTransferError, match="Failed to create .env file"):
            create_env_file(readonly_dir)


def test_overwrite_protection_user_declines() -> None:
    """Test that user declining to overwrite exits cleanly without error logging."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)

        # Create existing .env file to trigger overwrite protection
        (config_dir / ".env").write_text("existing content")

        # Mock typer.confirm to handle multiple confirmations:
        # 1. "Use default location?" -> False (we'll provide custom path)
        # 2. "Overwrite existing files?" -> False (decline overwrite)
        confirm_responses = [
            False,
            False,
        ]  # First: decline default, Second: decline overwrite

        with (
            patch("typer.confirm", side_effect=confirm_responses),
            patch(
                "typer.prompt", return_value=str(config_dir)
            ),  # Provide our temp dir path
        ):
            result = runner.invoke(
                app,
                [
                    "config",
                    "init",  # No target dir - triggers interactive mode
                    "--no-install-sequences",
                    "--no-install-completions",
                    "--no-install-schemas",
                ],
            )

            # Should exit cleanly with code 1, no "Unexpected error" in output
            assert result.exit_code == 1
            assert "Unexpected error" not in result.stdout
            assert "Configuration initialization complete" not in result.stdout


def test_overwrite_protection_user_accepts() -> None:
    """Test that user accepting overwrite continues normally."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)

        # Create existing .env file to trigger overwrite protection
        (config_dir / ".env").write_text("existing content")

        # Mock typer.confirm to handle multiple confirmations:
        # 1. "Use default location?" -> False (we'll provide custom path)
        # 2. Prompt for directory path (mocked via typer.prompt)
        # 3. "Overwrite existing files?" -> True (accept overwrite)
        confirm_responses = [
            False,
            True,
        ]  # First: decline default, Second: accept overwrite

        with (
            patch("typer.confirm", side_effect=confirm_responses),
            patch(
                "typer.prompt", return_value=str(config_dir)
            ),  # Provide our temp dir path
        ):
            result = runner.invoke(
                app,
                [
                    "config",
                    "init",  # No target dir - triggers interactive mode
                    "--no-install-sequences",
                    "--no-install-completions",
                    "--no-install-schemas",
                ],
            )

            # Should complete successfully
            assert result.exit_code == 0
            assert "Configuration initialization complete" in result.stdout
            assert "Unexpected error" not in result.stdout
