# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Additional tests for config-init interactive features and options.

These tests avoid network and real home writes by mocking subprocess and paths.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from typer.testing import CliRunner

from network_toolkit.cli import app
import network_toolkit.commands.config_init as config_init_mod


def test_config_init_yes_uses_default_location(monkeypatch: Any) -> None:
    """--yes with no target_dir uses default_config_root and creates files there."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Redirect default config root to a temp dir
        monkeypatch.setattr(config_init_mod, "default_config_root", lambda: tmp_path)

        result = runner.invoke(app, ["config-init", "--yes"])  # non-interactive

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

        result = runner.invoke(app, ["config-init", "--dry-run"], input=user_input)

        assert result.exit_code == 0
        # Nothing should be created in dry-run
        assert not (tmp_path / ".env").exists()
    # But the output should mention planned actions
    assert "Would create file:" in result.stdout
    assert "Would ensure directory:" in result.stdout


def test_config_init_install_sequences_triggers_git_clone(monkeypatch: Any) -> None:
    """--install-sequences should attempt a git clone, but we mock subprocess.run."""
    runner = CliRunner()

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_run(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        class _Result:
            returncode = 0
        return _Result()

    # Patch the subprocess.run used inside the module under test
    monkeypatch.setattr(config_init_mod.subprocess, "run", fake_run)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        result = runner.invoke(
            app,
            [
                "config-init",
                str(test_dir),
                "--install-sequences",
                "--git-url",
                "https://example.invalid/repo.git",
                "--git-ref",
                "ssh_multiplex",
            ],
        )

        assert result.exit_code == 0
        # We attempted to run git clone once
        assert any("git" in (args[0][0] if args and args[0] else "") for args in calls)


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
                "config-init",
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
        assert "Updated rc file:" in result.stdout or "Activated shell completion in:" in result.stdout
