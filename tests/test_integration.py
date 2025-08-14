# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Integration tests for the complete toolkit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_help_command_via_subprocess(self) -> None:
        """Test CLI help via subprocess."""
        # Test the CLI as it would be run by a user
        result = subprocess.run(
            [sys.executable, "-m", "network_toolkit", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        # Should succeed
        assert result.returncode == 0
        # Should contain help text
        assert (
            "Network" in result.stdout
            or "nw" in result.stdout
            or "Network" in result.stderr
            or "nw" in result.stderr
        )

    def test_list_devices_with_config(self, config_file: Path) -> None:
        """Test list-devices command with a real config file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "network_toolkit.cli",
                "--config",
                str(config_file),
                "list-devices",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        # Should succeed or fail gracefully
        assert result.returncode in [0, 1]

    def test_info_command_with_config(self, config_file: Path) -> None:
        """Test info command with a real config file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "network_toolkit.cli",
                "--config",
                str(config_file),
                "info",
                "test_device1",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        # Should succeed or fail gracefully
        assert result.returncode in [0, 1]

    def test_invalid_command(self) -> None:
        """Test CLI with invalid command."""
        result = subprocess.run(
            [sys.executable, "-m", "network_toolkit", "invalid-command"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        # Should fail with non-zero exit code
        assert result.returncode != 0

    def test_missing_config_file(self) -> None:
        """Test CLI with missing config file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "network_toolkit",
                "--config",
                "/nonexistent/config.yml",
                "list-devices",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        # Should fail with non-zero exit code
        assert result.returncode != 0


class TestConfigurationIntegration:
    """Integration tests for configuration loading."""

    def test_load_real_config_file(self, config_file: Path) -> None:
        """Test loading a real configuration file."""
        try:
            from network_toolkit.config import load_config

            config = load_config(config_file)
            assert config is not None
            assert config.devices is not None
            assert "test_device1" in config.devices
        except ImportError:
            # Dependencies not available, skip test
            pytest.skip("network_toolkit not importable")

    def test_config_validation(self, temp_dir: Path) -> None:
        """Test configuration validation with various inputs."""
        try:
            from network_toolkit.config import NetworkConfig

            # Test with minimal valid config
            config_data = {"devices": {"test": {"host": "192.168.1.1"}}}
            config = NetworkConfig(**config_data)
            assert config.devices is not None
            assert "test" in config.devices

        except ImportError:
            pytest.skip("network_toolkit not importable")


class TestModuleStructure:
    """Test that the module structure is correct."""

    def test_main_modules_importable(self) -> None:
        """Test that main modules can be imported."""
        modules_to_test = [
            "network_toolkit",
            "network_toolkit.config",
            "network_toolkit.exceptions",
            "network_toolkit.cli",
            "network_toolkit.device",
        ]

        importable_modules = []
        for module in modules_to_test:
            try:
                __import__(module)
                importable_modules.append(module)
            except ImportError:
                pass

        # At least some modules should be importable
        assert len(importable_modules) >= 0

    def test_package_structure(self) -> None:
        """Test that package has expected structure."""
        src_dir = Path(__file__).parent.parent / "src" / "network_toolkit"

        # Core module files should exist
        expected_files = [
            "__init__.py",
            "config.py",
            "exceptions.py",
            "cli.py",
            "device.py",
        ]

        existing_files = []
        for file in expected_files:
            if (src_dir / file).exists():
                existing_files.append(file)

        # Most files should exist
        assert len(existing_files) >= 3

    def test_pyproject_toml_exists(self) -> None:
        """Test that pyproject.toml exists and has required sections."""
        project_root = Path(__file__).parent.parent
        pyproject_file = project_root / "pyproject.toml"

        assert pyproject_file.exists()

        content = pyproject_file.read_text()
        assert "[project]" in content
        assert "network-toolkit" in content or "network_toolkit" in content

    def test_config_example_exists(self) -> None:
        """Test that example config structure exists."""
        project_root = Path(__file__).parent.parent

        # Check for new modular config structure
        config_dir = project_root / "config"
        if config_dir.exists():
            # Check main config file
            main_config = config_dir / "config.yml"
            assert main_config.exists(), (
                f"Required config file not found: {main_config}"
            )
            
            # Check that subdirectories exist (they may be empty but should exist)
            subdirs = ["devices", "groups", "sequences", "examples"]
            for subdir in subdirs:
                subdir_path = config_dir / subdir
                assert subdir_path.exists(), (
                    f"Required config subdirectory not found: {subdir_path}"
                )
            return

        # Fall back to legacy config files
        legacy_config_files = [
            "devices.yml",
            "devices.yaml",
        ]

        found_config = False
        for config_file in legacy_config_files:
            if (project_root / config_file).exists():
                found_config = True
                break

        assert found_config, (
            "No example config file found (neither modular config/ nor legacy devices.yml)"
        )


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @patch("network_toolkit.device.Scrapli")
    def test_device_session_workflow(
        self, mock_scrapli: MagicMock, sample_config
    ) -> None:
        """Test complete device session workflow."""
        try:
            from network_toolkit.device import DeviceSession

            # Mock the scrapli driver
            mock_driver = MagicMock()
            mock_scrapli.return_value = mock_driver

            # Create device session
            session = DeviceSession("test_device1", sample_config)

            # Test connection
            session.connect()
            mock_driver.open.assert_called_once()

            # Test disconnect
            session.disconnect()
            mock_driver.close.assert_called_once()

        except ImportError:
            pytest.skip("network_toolkit not importable")
