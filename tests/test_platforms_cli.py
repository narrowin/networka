# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for platforms CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app

runner = CliRunner()


class TestPlatformsListCommand:
    """Tests for the 'nw platforms list' command."""

    def test_list_all_platforms(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Show exact definition names and the active source next to registry data."""
        monkeypatch.setattr("scrapli.cli.CLI_DEFINITIONS_PATH_OVERRIDE", None)
        result = runner.invoke(app, ["platforms", "list"])
        assert result.exit_code == 0
        assert "Network Platforms" in result.stdout
        assert "mikrotik_routeros" in result.stdout
        assert "cisco_ios" in result.stdout
        assert "cisco_iosxe" in result.stdout
        assert "cisco_nxos" in result.stdout

        definitions = result.stdout.split("Active Scrapli definitions", 1)[1]
        assert "Packaged Scrapli" in definitions
        assert "cumulus_linux" in definitions
        assert "cisco_ios," not in definitions

        (tmp_path / "cumulus_linux.yaml").touch()
        monkeypatch.setattr("scrapli.cli.CLI_DEFINITIONS_PATH_OVERRIDE", str(tmp_path))
        result = runner.invoke(app, ["platforms", "list"])
        assert result.exit_code == 0
        registry, definitions = result.stdout.split("Active Scrapli definitions", 1)
        assert "mikrotik_routeros" in registry
        assert f"SCRAPLI_DEFINITIONS_PATH ({tmp_path})" in definitions
        assert "cumulus_linux" in definitions
        assert "mikrotik_routeros" not in definitions

        result = runner.invoke(app, ["platforms", "info", "cumulus_linux"])
        assert result.exit_code == 0
        assert "Scrapli definition: cumulus_linux" in result.stdout
        assert str(tmp_path / "cumulus_linux.yaml") in result.stdout
        assert "Registered vendor operations: None" in result.stdout

    def test_list_implemented_platforms(self) -> None:
        """Test filtering by implemented status."""
        result = runner.invoke(app, ["platforms", "list", "--status", "implemented"])
        assert result.exit_code == 0
        assert "mikrotik_routeros" in result.stdout
        assert "cisco_ios" in result.stdout
        assert "cisco_iosxe" in result.stdout
        # Should not include sequences_only or planned
        assert "cisco_nxos" not in result.stdout
        assert "cisco_iosxr" not in result.stdout

    def test_list_sequences_only_platforms(self) -> None:
        """Test filtering by sequences_only status."""
        result = runner.invoke(app, ["platforms", "list", "--status", "sequences_only"])
        assert result.exit_code == 0
        assert "cisco_nxos" in result.stdout
        assert "arista_eos" in result.stdout
        assert "juniper_junos" in result.stdout
        # Should not include implemented platforms
        assert "mikrotik_routeros" not in result.stdout

    def test_list_planned_platforms(self) -> None:
        """Test filtering by planned status."""
        result = runner.invoke(app, ["platforms", "list", "--status", "planned"])
        assert result.exit_code == 0
        assert "cisco_iosxr" in result.stdout
        assert "nokia_srlinux" in result.stdout
        assert "linux" in result.stdout
        assert "generic" in result.stdout
        # Should not include implemented platforms
        assert "mikrotik_routeros" not in result.stdout

    def test_list_invalid_status(self) -> None:
        """Test that invalid status returns error."""
        result = runner.invoke(app, ["platforms", "list", "--status", "invalid"])
        assert result.exit_code == 1
        assert "Invalid status" in result.stdout

    def test_list_cisco_vendor(self) -> None:
        """Test filtering by cisco vendor."""
        result = runner.invoke(app, ["platforms", "list", "--vendor", "cisco"])
        assert result.exit_code == 0
        assert "cisco_ios" in result.stdout
        assert "cisco_iosxe" in result.stdout
        assert "cisco_nxos" in result.stdout
        assert "cisco_iosxr" in result.stdout
        # Should not include other vendors
        assert "mikrotik_routeros" not in result.stdout
        assert "arista_eos" not in result.stdout

    def test_list_mikrotik_vendor(self) -> None:
        """Test filtering by mikrotik vendor."""
        result = runner.invoke(app, ["platforms", "list", "--vendor", "mikrotik"])
        assert result.exit_code == 0
        assert "mikrotik_routeros" in result.stdout
        # Should not include other vendors
        assert "cisco_ios" not in result.stdout

    def test_list_vendor_case_insensitive(self) -> None:
        """Test that vendor filtering is case insensitive."""
        result = runner.invoke(app, ["platforms", "list", "--vendor", "CISCO"])
        assert result.exit_code == 0
        assert "cisco_ios" in result.stdout

    def test_list_nonexistent_vendor(self) -> None:
        """Test that nonexistent vendor returns error."""
        result = runner.invoke(app, ["platforms", "list", "--vendor", "nonexistent"])
        assert result.exit_code == 1
        assert "No platforms found" in result.stdout

    def test_list_config_backup_capability(self) -> None:
        """Test filtering by config_backup capability."""
        result = runner.invoke(
            app, ["platforms", "list", "--capability", "config_backup"]
        )
        assert result.exit_code == 0
        assert "mikrotik_routeros" in result.stdout
        assert "cisco_ios" in result.stdout
        assert "cisco_iosxe" in result.stdout
        # Should not include platforms without this capability
        assert "cisco_nxos" not in result.stdout

    def test_list_firmware_upgrade_capability(self) -> None:
        """Test filtering by firmware_upgrade capability."""
        result = runner.invoke(
            app, ["platforms", "list", "--capability", "firmware_upgrade"]
        )
        assert result.exit_code == 0
        assert "mikrotik_routeros" in result.stdout
        assert "cisco_ios" in result.stdout
        assert "cisco_iosxe" in result.stdout

    def test_list_comprehensive_backup_capability(self) -> None:
        """Test filtering by comprehensive_backup capability."""
        result = runner.invoke(
            app, ["platforms", "list", "--capability", "comprehensive_backup"]
        )
        assert result.exit_code == 0
        assert "mikrotik_routeros" in result.stdout
        assert "cisco_ios" in result.stdout
        assert "cisco_iosxe" in result.stdout

    def test_list_invalid_capability(self) -> None:
        """Test that invalid capability returns error."""
        result = runner.invoke(
            app, ["platforms", "list", "--capability", "invalid_capability"]
        )
        assert result.exit_code == 1
        assert "Invalid capability" in result.stdout

    def test_list_shows_capability_checkmarks(self) -> None:
        """Test that capability columns show checkmarks for implemented platforms."""
        result = runner.invoke(app, ["platforms", "list"])
        assert result.exit_code == 0
        # Check for checkmarks in output (using UTF-8 checkmark)
        lines = result.stdout.split("Active Scrapli definitions", 1)[0].splitlines()
        # Find mikrotik line and verify it has checkmarks
        mikrotik_line = [line for line in lines if "mikrotik_routeros" in line]
        assert len(mikrotik_line) == 1
        # Should have checkmarks for capabilities
        assert "✓" in mikrotik_line[0]

    def test_list_shows_dashes_for_no_capabilities(self) -> None:
        """Test that platforms without capabilities show dashes."""
        result = runner.invoke(app, ["platforms", "list"])
        assert result.exit_code == 0
        lines = result.stdout.split("Active Scrapli definitions", 1)[0].splitlines()
        # Find planned platform line
        planned_line = [line for line in lines if "cisco_iosxr" in line]
        assert len(planned_line) == 1
        # Should have dashes for no capabilities
        assert "—" in planned_line[0] or "-" in planned_line[0]


class TestPlatformsInfoCommand:
    """Tests for the 'nw platforms info' command."""

    def test_info_mikrotik_routeros(
        self, monkeypatch: pytest.MonkeyPatch, test_config_dir: Path
    ) -> None:
        """Show the definition, registered operations, and sequences with sources."""
        monkeypatch.setattr("scrapli.cli.CLI_DEFINITIONS_PATH_OVERRIDE", None)
        monkeypatch.setenv("NW_CONFIG_DIR", str(test_config_dir))
        result = runner.invoke(app, ["platforms", "info", "mikrotik_routeros"])
        assert result.exit_code == 0
        assert "mikrotik_routeros" in result.stdout
        assert "MikroTik RouterOS" in result.stdout
        assert "MikroTik" in result.stdout
        assert "Implemented" in result.stdout
        assert "Config Backup" in result.stdout
        assert "Firmware Upgrade" in result.stdout
        assert ".npk" in result.stdout
        assert (
            "Packaged Scrapli (scrapli.definitions/mikrotik_routeros.yaml)"
            in result.stdout
        )
        assert "Platform sequences and sources" in result.stdout
        assert "health_check (packaged:" in result.stdout
        assert "/builtin_sequences/mikrotik_routeros/common.yml" in result.stdout

    def test_info_cisco_ios(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Show the IOS connection alias separately from IOS operations."""
        monkeypatch.setattr("scrapli.cli.CLI_DEFINITIONS_PATH_OVERRIDE", None)
        result = runner.invoke(app, ["platforms", "info", "cisco_ios"])
        assert result.exit_code == 0
        assert "cisco_ios" in result.stdout
        assert "Cisco IOS" in result.stdout
        assert "Cisco" in result.stdout
        assert "Implemented" in result.stdout
        assert ".bin" in result.stdout or ".tar" in result.stdout
        assert "Scrapli alias: cisco_ios → cisco_iosxe" in result.stdout
        assert "scrapli.definitions/cisco_iosxe.yaml" in result.stdout

    def test_info_sequences_only_platform(self) -> None:
        """Test showing info for sequences_only platform."""
        result = runner.invoke(app, ["platforms", "info", "cisco_nxos"])
        assert result.exit_code == 0
        assert "cisco_nxos" in result.stdout
        assert "Sequences Only" in result.stdout
        assert "Not configured" in result.stdout

    def test_info_planned_platform(self) -> None:
        """Test showing info for planned platform."""
        result = runner.invoke(app, ["platforms", "info", "cisco_iosxr"])
        assert result.exit_code == 0
        assert "cisco_iosxr" in result.stdout
        assert "Planned" in result.stdout

    def test_info_nonexistent_platform(self) -> None:
        """Test that nonexistent platform returns error."""
        result = runner.invoke(app, ["platforms", "info", "nonexistent"])
        assert result.exit_code == 1
        assert "Platform not found" in result.stdout
        assert "nw platforms list" in result.stdout

    def test_info_shows_all_capabilities(self) -> None:
        """Test that info shows all capability types."""
        result = runner.invoke(app, ["platforms", "info", "mikrotik_routeros"])
        assert result.exit_code == 0
        assert "Config Backup" in result.stdout
        assert "Firmware Upgrade" in result.stdout
        assert "Firmware Downgrade" in result.stdout
        assert "BIOS Upgrade" in result.stdout
        assert "Comprehensive Backup" in result.stdout

    def test_info_shows_documentation_path(self) -> None:
        """Test that info shows documentation path when available."""
        result = runner.invoke(app, ["platforms", "info", "mikrotik_routeros"])
        assert result.exit_code == 0
        assert "Documentation:" in result.stdout
        assert "vendors/mikrotik/index.md" in result.stdout

    def test_info_shows_operations_class(self) -> None:
        """Test that info shows operations class for implemented platforms."""
        result = runner.invoke(app, ["platforms", "info", "mikrotik_routeros"])
        assert result.exit_code == 0
        assert "Operations Class:" in result.stdout
        # The class name might be split across lines due to formatting, check for key parts
        assert (
            "MikroTikRouterOS" in result.stdout
            or "mikrotik_routeros.operations" in result.stdout
        )


class TestPlatformsCommand:
    """Tests for the platforms command group."""

    def test_platforms_requires_subcommand(self) -> None:
        """Test that platforms command requires a subcommand."""
        result = runner.invoke(app, ["platforms"])
        # Should show usage/help when no subcommand provided
        assert result.exit_code != 0


__all__ = [
    "TestPlatformsCommand",
    "TestPlatformsInfoCommand",
    "TestPlatformsListCommand",
]
