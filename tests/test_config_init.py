# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for config-init command."""

from __future__ import annotations

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from network_toolkit.cli import app


def test_config_init_creates_minimal_environment() -> None:
    """Test that config-init creates a complete minimal environment."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Run config init in the test directory
        result = runner.invoke(app, ["config", "init", str(test_dir)])

        assert result.exit_code == 0
        assert "Configuration initialization complete" in result.stdout

        # Check that all expected files and directories were created
        assert (test_dir / ".env").exists()
        assert (test_dir / "config.yml").exists()
        assert (test_dir / "devices" / "mikrotik.yml").exists()
        assert (test_dir / "devices" / "cisco.yml").exists()
        assert (test_dir / "groups" / "main.yml").exists()
        assert (test_dir / "sequences" / "basic.yml").exists()

        # Check .env content
        env_content = (test_dir / ".env").read_text()
        assert "NW_USER_DEFAULT=admin" in env_content
        assert "NW_PASSWORD_DEFAULT=changeme123" in env_content

        # Check config.yml content
        config_content = (test_dir / "config.yml").read_text()
        assert "general:" in config_content
        assert 'transport: "ssh"' in config_content

        # Check devices content
        devices_content = (test_dir / "devices" / "mikrotik.yml").read_text()
        assert "sw-office-01:" in devices_content
        assert "mikrotik_routeros" in devices_content

        # Check groups content
        groups_content = (test_dir / "groups" / "main.yml").read_text()
        assert "office_switches:" in groups_content
        assert "match_tags:" in groups_content

        # Check sequences content
        sequences_content = (test_dir / "sequences" / "basic.yml").read_text()
        assert "system_info:" in sequences_content
        assert "/system/identity/print" in sequences_content


def test_config_init_force_overwrite() -> None:
    """Test that --force overwrites existing files."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create an existing .env file
        env_file = test_dir / ".env"
        env_file.write_text("OLD_CONTENT=test")

        # Run config init with --force
        result = runner.invoke(app, ["config", "init", str(test_dir), "--force"])

        assert result.exit_code == 0

        # Check that the file was overwritten
        env_content = env_file.read_text()
        assert "NW_USER_DEFAULT=admin" in env_content
        assert "OLD_CONTENT=test" not in env_content


def test_config_init_fails_without_force() -> None:
    """Test that config-init fails when files exist without --force."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create an existing .env file
        (test_dir / ".env").write_text("OLD_CONTENT=test")

        # Run config init without --force
        result = runner.invoke(app, ["config", "init", str(test_dir)])

        assert result.exit_code == 1
        assert "already exist" in result.stdout
        assert "Use --force to overwrite" in result.stdout


def test_config_init_help() -> None:
    """Test that config-init --help works."""
    runner = CliRunner()
    result = runner.invoke(app, ["config", "init", "--help"])

    assert result.exit_code == 0
    assert (
        "Initialize a network toolkit configuration in OS-appropriate location"
        in result.stdout
    )
    assert "Creates a complete starter configuration" in result.stdout
    assert "--force" in result.stdout
