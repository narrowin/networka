# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for multi-vendor support functionality."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from network_toolkit.config import VendorSequence, load_config


@pytest.fixture
def multi_vendor_config_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with multi-vendor configuration."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_dir = Path(tmp_dir)

        # Create main config
        main_config: dict[str, dict[str, int | str]] = {
            "general": {
                "results_dir": str(config_dir / "results"),
                "timeout": 30,
            }
        }
        with (config_dir / "config.yml").open("w") as f:
            yaml.dump(main_config, f)

        # Create devices config with multi-vendor devices
        devices_config: dict[str, dict[str, dict[str, str | list[str]]]] = {
            "devices": {
                "mikrotik-sw1": {
                    "host": "10.0.1.10",
                    "device_type": "mikrotik_routeros",
                    "description": "MikroTik Switch",
                    "tags": ["switch", "mikrotik"],
                },
                "cisco-sw1": {
                    "host": "10.0.1.20",
                    "device_type": "cisco_iosxe",
                    "description": "Cisco Switch",
                    "tags": ["switch", "cisco"],
                },
                "arista-sw1": {
                    "host": "10.0.1.30",
                    "device_type": "arista_eos",
                    "description": "Arista Switch",
                    "tags": ["switch", "arista"],
                },
            }
        }
        with (config_dir / "devices.yml").open("w") as f:
            yaml.dump(devices_config, f)

        # Create groups config
        groups_config: dict[str, dict[str, dict[str, str | list[str]]]] = {
            "groups": {
                "all_switches": {
                    "description": "All switches",
                    "match_tags": ["switch"],
                },
                "cisco_devices": {
                    "description": "Cisco devices",
                    "match_tags": ["cisco"],
                },
            }
        }
        with (config_dir / "groups.yml").open("w") as f:
            yaml.dump(groups_config, f)

        # Create sequences config with vendor platform definitions
        sequences_config: dict[str, dict[str, dict[str, str | list[str]]]] = {
            "vendor_platforms": {
                "mikrotik_routeros": {
                    "description": "MikroTik RouterOS devices",
                    "sequence_path": "sequences/mikrotik_routeros",
                    "default_files": ["common.yml"],
                },
                "cisco_iosxe": {
                    "description": "Cisco IOS-XE devices",
                    "sequence_path": "sequences/cisco_iosxe",
                    "default_files": ["common.yml"],
                },
                "arista_eos": {
                    "description": "Arista EOS devices",
                    "sequence_path": "sequences/arista_eos",
                    "default_files": ["common.yml"],
                },
            }
        }
        with (config_dir / "sequences.yml").open("w") as f:
            yaml.dump(sequences_config, f)

        # Create vendor sequence directories and files
        vendor_dirs: dict[str, dict[str, dict[str, str | int | list[str]]]] = {
            "mikrotik_routeros": {
                "system_info": {
                    "description": "MikroTik system information",
                    "category": "information",
                    "timeout": 60,
                    "commands": [
                        "/system/identity/print",
                        "/system/resource/print",
                        "/system/routerboard/print",
                    ],
                },
                "health_check": {
                    "description": "MikroTik health check",
                    "category": "monitoring",
                    "timeout": 45,
                    "commands": [
                        "/system/resource/print",
                        "/interface/print stats",
                    ],
                },
            },
            "cisco_iosxe": {
                "system_info": {
                    "description": "Cisco system information",
                    "category": "information",
                    "timeout": 60,
                    "commands": [
                        "show version",
                        "show inventory",
                        "show environment all",
                    ],
                },
                "health_check": {
                    "description": "Cisco health check",
                    "category": "monitoring",
                    "timeout": 45,
                    "commands": [
                        "show processes cpu",
                        "show interfaces summary",
                    ],
                },
            },
            "arista_eos": {
                "system_info": {
                    "description": "Arista system information",
                    "category": "information",
                    "timeout": 60,
                    "commands": [
                        "show version",
                        "show inventory",
                        "show environment",
                    ],
                },
            },
        }

        for vendor, sequences in vendor_dirs.items():
            vendor_dir = config_dir / "sequences" / vendor
            vendor_dir.mkdir(parents=True, exist_ok=True)

            vendor_config: dict[str, dict[str, dict[str, str | int | list[str]]]] = {
                "sequences": sequences
            }
            with (vendor_dir / "common.yml").open("w") as f:
                yaml.dump(vendor_config, f)

        yield config_dir


class TestMultiVendorSupport:
    """Test multi-vendor support functionality."""

    def test_load_multi_vendor_config(self, multi_vendor_config_dir: Path) -> None:
        """Test loading multi-vendor configuration."""
        config = load_config(multi_vendor_config_dir)

        # Verify basic structure
        assert config.devices is not None
        assert config.vendor_platforms is not None
        assert config.vendor_sequences is not None

        # Verify vendor platforms
        assert "mikrotik_routeros" in config.vendor_platforms
        assert "cisco_iosxe" in config.vendor_platforms
        assert "arista_eos" in config.vendor_platforms

        # Verify devices with correct types
        assert "mikrotik-sw1" in config.devices
        assert config.devices["mikrotik-sw1"].device_type == "mikrotik_routeros"
        assert "cisco-sw1" in config.devices
        assert config.devices["cisco-sw1"].device_type == "cisco_iosxe"

        # Verify vendor sequences were loaded
        assert "mikrotik_routeros" in config.vendor_sequences
        assert "cisco_iosxe" in config.vendor_sequences
        assert "arista_eos" in config.vendor_sequences

        # Verify specific sequences
        mikrotik_sequences = config.vendor_sequences["mikrotik_routeros"]
        assert "system_info" in mikrotik_sequences
        assert "health_check" in mikrotik_sequences

        cisco_sequences = config.vendor_sequences["cisco_iosxe"]
        assert "system_info" in cisco_sequences
        assert "health_check" in cisco_sequences

    def test_vendor_sequence_resolution(self, multi_vendor_config_dir: Path) -> None:
        """Test vendor-specific sequence command resolution."""
        config = load_config(multi_vendor_config_dir)

        # Test MikroTik sequence resolution
        mikrotik_commands = config.resolve_sequence_commands(
            "system_info", "mikrotik-sw1"
        )
        assert mikrotik_commands is not None
        assert "/system/identity/print" in mikrotik_commands
        assert "/system/resource/print" in mikrotik_commands
        assert "/system/routerboard/print" in mikrotik_commands

        # Test Cisco sequence resolution
        cisco_commands = config.resolve_sequence_commands("system_info", "cisco-sw1")
        assert cisco_commands is not None
        assert "show version" in cisco_commands
        assert "show inventory" in cisco_commands
        assert "show environment all" in cisco_commands

        # Test Arista sequence resolution
        arista_commands = config.resolve_sequence_commands("system_info", "arista-sw1")
        assert arista_commands is not None
        assert "show version" in arista_commands
        assert "show inventory" in arista_commands
        assert "show environment" in arista_commands

    def test_vendor_sequence_resolution_not_found(
        self, multi_vendor_config_dir: Path
    ) -> None:
        """Test sequence resolution when sequence not found."""
        config = load_config(multi_vendor_config_dir)

        # Test non-existent sequence
        commands = config.resolve_sequence_commands("non_existent", "mikrotik-sw1")
        assert commands is None

        # Test sequence that doesn't exist for specific vendor
        commands = config.resolve_sequence_commands("health_check", "arista-sw1")
        assert commands is None  # Arista doesn't have health_check in our test config

    def test_vendor_sequence_models(self) -> None:
        """Test VendorSequence model validation."""
        # Test valid sequence
        sequence = VendorSequence(
            description="Test sequence",
            category="test",
            timeout=60,
            commands=["command1", "command2"],
            device_types=["switch"],
        )
        assert sequence.description == "Test sequence"
        assert sequence.category == "test"
        assert sequence.timeout == 60
        assert sequence.commands == ["command1", "command2"]
        assert sequence.device_types == ["switch"]

        # Test minimal sequence
        minimal_sequence = VendorSequence(
            description="Minimal test", commands=["command1"]
        )
        assert minimal_sequence.description == "Minimal test"
        assert minimal_sequence.commands == ["command1"]
        assert minimal_sequence.category is None
        assert minimal_sequence.timeout is None
        assert minimal_sequence.device_types is None

    def test_device_type_validation(self, multi_vendor_config_dir: Path) -> None:
        """Test that device types are properly configured."""
        config = load_config(multi_vendor_config_dir)

        # Verify each device has correct device_type
        devices = config.devices
        assert devices is not None

        mikrotik_device = devices["mikrotik-sw1"]
        assert mikrotik_device.device_type == "mikrotik_routeros"

        cisco_device = devices["cisco-sw1"]
        assert cisco_device.device_type == "cisco_iosxe"

        arista_device = devices["arista-sw1"]
        assert arista_device.device_type == "arista_eos"

    def test_multi_vendor_group_resolution(self, multi_vendor_config_dir: Path) -> None:
        """Test that groups work with multi-vendor devices."""
        config = load_config(multi_vendor_config_dir)

        # Test all_switches group (should include all devices)
        all_switches = config.get_group_members("all_switches")
        assert "mikrotik-sw1" in all_switches
        assert "cisco-sw1" in all_switches
        assert "arista-sw1" in all_switches

        # Test vendor-specific group
        cisco_devices = config.get_group_members("cisco_devices")
        assert "cisco-sw1" in cisco_devices
        assert "mikrotik-sw1" not in cisco_devices
        assert "arista-sw1" not in cisco_devices

    def test_missing_vendor_sequences_graceful_handling(
        self, multi_vendor_config_dir: Path
    ) -> None:
        """Test graceful handling when vendor sequence files are missing."""
        config = load_config(multi_vendor_config_dir)

        # Should return None gracefully for unknown device, not crash
        commands = config.resolve_sequence_commands("system_info", "unknown-device")
        assert commands is None

    def test_vendor_sequence_command_count(self, multi_vendor_config_dir: Path) -> None:
        """Test that vendor sequences have expected command counts."""
        config = load_config(multi_vendor_config_dir)

        # Test MikroTik system_info has 3 commands
        mikrotik_commands = config.resolve_sequence_commands(
            "system_info", "mikrotik-sw1"
        )
        assert mikrotik_commands is not None
        assert len(mikrotik_commands) == 3

        # Test Cisco system_info has 3 commands
        cisco_commands = config.resolve_sequence_commands("system_info", "cisco-sw1")
        assert cisco_commands is not None
        assert len(cisco_commands) == 3

        # Test MikroTik health_check has 2 commands
        mikrotik_health = config.resolve_sequence_commands(
            "health_check", "mikrotik-sw1"
        )
        assert mikrotik_health is not None
        assert len(mikrotik_health) == 2
