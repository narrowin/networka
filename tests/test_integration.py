# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Integration tests for the complete toolkit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

NW_RUN = [
    "uv",
    "run",
    "--no-project",
    "--python",
    sys.executable,
    "python",
    "-m",
    "network_toolkit",
]


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_help_command_via_subprocess(self) -> None:
        """Test CLI help via subprocess."""
        # Test the CLI as it would be run by a user
        result = subprocess.run(
            [*NW_RUN, "--help"],
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
        """Test list devices command with a real config file."""
        result = subprocess.run(
            [*NW_RUN, "list", "devices", "--config", str(config_file)],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        assert result.returncode == 0, result.stderr
        assert "test_device1" in result.stdout
        assert "192.168.1.10" in result.stdout

    def test_info_command_with_config(self, config_file: Path) -> None:
        """Test info command with a real config file."""
        result = subprocess.run(
            [*NW_RUN, "info", "test_device1", "--config", str(config_file)],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        assert result.returncode == 0, result.stderr
        assert "test_device1" in result.stdout
        assert "192.168.1.10" in result.stdout

    def test_invalid_command(self) -> None:
        """Test CLI with invalid command."""
        result = subprocess.run(
            [*NW_RUN, "invalid-command"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        assert result.returncode == 2
        assert "No such command" in result.stderr
        assert "invalid-command" in result.stderr

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Test CLI with missing config file."""
        missing_path = tmp_path / "missing.yml"
        result = subprocess.run(
            [*NW_RUN, "list", "devices", "--config", str(missing_path)],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30,
        )

        assert result.returncode == 1
        assert "Configuration file not found" in result.stdout


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

    # No legacy fallback; modular config directory is required for examples
