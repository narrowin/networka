"""Test info command credential source display."""

import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from network_toolkit.cli import app


class TestInfoCommandCredentials:
    """Test credential source display in info command."""

    def test_info_shows_credential_sources(self, tmp_path: Path) -> None:
        """Test that info command shows credential sources."""
        # Create test configuration
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create main config.yml file (required for modular config)
        config_file = config_dir / "config.yml"
        config_file.write_text(
            """
general:
  timeout: 30
  port: 22
"""
        )

        # Create devices.yml directly in config directory (not in subdirectory)
        devices_file = config_dir / "devices.yml"
        devices_config = {
            "devices": {
                "test_device1": {
                    "host": "192.168.1.100",
                    "device_type": "mikrotik_routeros",
                    "groups": ["test_group"],
                }
            }
        }
        devices_file.write_text(yaml.safe_dump(devices_config))

        # Create groups directory for group config
        groups_dir = config_dir / "groups"
        groups_dir.mkdir()

        # Create groups config
        groups_config = groups_dir / "groups.yml"
        groups_config.write_text(
            """
groups:
  test_group:
    description: "Test group"
    match_tags: ["test"]
    credentials:
      user: "group_user"
      password: "group_pass"
"""
        )

        # Set environment variables
        os.environ["NW_USER_DEFAULT"] = "default_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "default_pass"
        os.environ["NW_SHOW_PLAINTEXT_PASSWORDS"] = "1"

        try:
            runner = CliRunner()

            result = runner.invoke(
                app, ["info", "test_device1", "--config", str(config_dir)]
            )

            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")

            # Check that command succeeded
            if result.exit_code != 0:
                pytest.fail(
                    f"Command failed with exit code {result.exit_code}. Output: {result.output}"
                )

            # Check that credential source information is shown in table
            assert "Credentials" in result.output
            assert "Environment variables" in result.output

        finally:
            # Clean up environment
            for var in [
                "NW_USER_DEFAULT",
                "NW_PASSWORD_DEFAULT",
                "NW_SHOW_PLAINTEXT_PASSWORDS",
            ]:
                if var in os.environ:
                    del os.environ[var]

    def test_info_hides_password_by_default(self, tmp_path: Path) -> None:
        """Test that password is hidden by default."""
        # Create minimal test configuration
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create main config.yml file (required for modular config)
        config_file = config_dir / "config.yml"
        config_file.write_text(
            """
general:
  timeout: 30
  port: 22
"""
        )

        # Create devices.yml directly in config directory (not in subdirectory)
        devices_config = config_dir / "devices.yml"
        devices_config.write_text(
            """
devices:
  test_device1:
    host: "192.168.1.1"
    device_type: "mikrotik_routeros"
    platform: "arm"
"""
        )

        # Set minimal environment
        os.environ["NW_USER_DEFAULT"] = "test_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "test_pass"

        try:
            runner = CliRunner()
            result = runner.invoke(
                app, ["info", "test_device1", "--config", str(config_dir)]
            )

            assert result.exit_code == 0
            # When NW_SHOW_PLAINTEXT_PASSWORDS is not set, password should be hidden
            # Ensure only credential source is shown, not actual credentials
            assert "Credentials" in result.output
            assert "Environment variables" in result.output
            # Verify no actual credential values are shown
            assert (
                "test_pass" not in result.output
            )  # Ensure password is not shown in plaintext

        finally:
            # Clean up environment
            for var in ["NW_USER_DEFAULT", "NW_PASSWORD_DEFAULT"]:
                if var in os.environ:
                    del os.environ[var]
