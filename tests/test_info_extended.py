# SPDX-License-Identifier: MIT
"""Tests for group and mixed-target information in `nw info`."""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from network_toolkit.cli import app


class TestInfoExtendedFunctionality:
    def test_info_group(self, config_file: Path) -> None:
        """Show a group's configured description and members."""
        result = CliRunner().invoke(
            app, ["info", "lab_devices", "--config", str(config_file)]
        )

        assert result.exit_code == 0, result.output
        assert "Group: lab_devices" in result.output
        assert "Lab devices" in result.output
        assert "Device Count" in result.output
        assert "test_device1, test_device2" in result.output

    def test_info_multiple_targets_mixed(self, config_file: Path) -> None:
        """Render device, group and vendor sequence data in a single command."""
        result = CliRunner().invoke(
            app,
            [
                "info",
                "test_device1,lab_devices,system_info",
                "--config",
                str(config_file),
                "--vendor",
                "mikrotik_routeros",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Device: test_device1" in result.output
        assert "Group: lab_devices" in result.output
        assert "system_info" in result.output
        assert "/system/identity/print" in result.output

    def test_info_group_no_members(self, config_file: Path) -> None:
        """Render the zero member count when a group's tags match no devices."""
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        data["device_groups"]["empty_group"] = {
            "description": "Empty group",
            "match_tags": ["unused"],
        }
        config_file.write_text(yaml.safe_dump(data), encoding="utf-8")

        result = CliRunner().invoke(
            app,
            [
                "info",
                "empty_group",
                "--config",
                str(config_file),
                "--output-mode",
                "raw",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "group=empty_group source=config device_count=0" in result.output

    def test_info_unknown_target(self, config_file: Path) -> None:
        """Report an unknown target while still rendering valid targets."""
        result = CliRunner().invoke(
            app,
            ["info", "test_device1,nonexistent_target", "--config", str(config_file)],
        )

        assert result.exit_code == 0, result.output
        assert "Device: test_device1" in result.output
        assert "Unknown target: nonexistent_target" in result.output
