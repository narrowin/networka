"""
Test configuration loading against real-world config structure.

This test suite verifies that the configuration loading works with the actual
config directory structure in the repository, catching issues that synthetic
test fixtures might miss.
"""

from pathlib import Path

import pytest

from network_toolkit.config import load_config, load_modular_config


class TestRealWorldConfigLoading:
    """Test configuration loading with actual config files."""

    def test_load_config_with_directory_path(self):
        """Test loading config by pointing to the config directory."""
        config_dir = Path("config")
        if not config_dir.exists():
            pytest.skip("Config directory not found - test requires real config files")

        config = load_config(config_dir)

        # Verify basic structure loaded
        assert (
            config.devices is not None
        ), "Devices should be loaded from config/devices/"
        assert (
            config.device_groups is not None
        ), "Groups should be loaded from config/groups/"

        # Verify vendor sequences are auto-discovered
        assert (
            config.vendor_sequences is not None
        ), "Vendor sequences should be auto-discovered"
        assert (
            len(config.vendor_sequences) > 0
        ), "Should discover vendor sequences from config/sequences/"

        # Verify specific vendors we know exist
        expected_vendors = [
            "mikrotik_routeros",
            "cisco_iosxe",
            "cisco_nxos",
            "juniper_junos",
            "arista_eos",
        ]
        for vendor in expected_vendors:
            vendor_dir = config_dir / "sequences" / vendor
            if vendor_dir.exists():
                assert (
                    vendor in config.vendor_sequences
                ), f"Should auto-discover {vendor} sequences"
                assert (
                    len(config.vendor_sequences[vendor]) > 0
                ), f"Should load sequences for {vendor}"

    def test_load_config_with_config_yml_path(self):
        """Test loading config by pointing to config.yml file - should detect modular structure."""
        config_file = Path("config/config.yml")
        if not config_file.exists():
            pytest.skip("Config file not found - test requires real config files")

        config = load_config(config_file)

        # Should detect that this is part of a modular config and load everything
        assert (
            config.devices is not None
        ), "Should load devices even when pointing to config.yml"
        assert len(config.devices) > 0, "Should find devices in config/devices/"

        assert (
            config.vendor_sequences is not None
        ), "Should auto-discover vendor sequences"
        assert (
            len(config.vendor_sequences) > 0
        ), "Should find vendor sequences in config/sequences/"

    def test_vendor_sequence_auto_discovery(self):
        """Test that vendor sequence auto-discovery works correctly."""
        config_dir = Path("config")
        if not config_dir.exists():
            pytest.skip("Config directory not found")

        config = load_modular_config(config_dir)

        # Check each vendor directory exists and sequences are loaded
        sequences_dir = config_dir / "sequences"
        if sequences_dir.exists():
            for vendor_dir in sequences_dir.iterdir():
                if vendor_dir.is_dir() and not vendor_dir.name.startswith("."):
                    vendor_name = vendor_dir.name

                    # Should have auto-discovered this vendor
                    assert config.vendor_sequences is not None
                    assert (
                        vendor_name in config.vendor_sequences
                    ), f"Should auto-discover {vendor_name}"

                    # Check for common.yml file and verify sequences loaded
                    common_file = vendor_dir / "common.yml"
                    if common_file.exists():
                        vendor_sequences = config.vendor_sequences[vendor_name]
                        assert (
                            len(vendor_sequences) > 0
                        ), f"Should load sequences from {common_file}"

                        # Verify sequences have required attributes
                        for seq_name, sequence in vendor_sequences.items():
                            assert hasattr(
                                sequence, "description"
                            ), f"Sequence {seq_name} should have description"
                            assert hasattr(
                                sequence, "commands"
                            ), f"Sequence {seq_name} should have commands"
                            assert (
                                len(sequence.commands) > 0
                            ), f"Sequence {seq_name} should have commands"

    def test_cli_list_sequences_works_after_fix(self):
        """Test that CLI list sequences command works after the fix."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # Test with config directory
        result = runner.invoke(app, ["list", "sequences", "--config", "config"])

        # Should not fail and should show sequences
        assert (
            result.exit_code == 0
        ), f"CLI should work after fix. Output: {result.output}"
        assert "No data available" not in result.output, "Should find sequences"
        assert "Vendor Sequences" in result.output, "Should show vendor sequences"

    def test_devices_loading_from_real_config(self):
        """Test that devices are actually loaded from the real config files."""
        config_dir = Path("config")
        if not config_dir.exists():
            pytest.skip("Config directory not found")

        config = load_config(config_dir)

        # Check that we loaded devices from the actual device files
        device_files = list((config_dir / "devices").glob("*.yml"))
        if device_files:
            assert config.devices is not None, "Should load devices"
            assert len(config.devices) > 0, "Should load devices from device files"

            # Verify device structure
            for device_name, device in config.devices.items():
                assert hasattr(device, "host"), f"Device {device_name} should have host"
                assert hasattr(
                    device, "device_type"
                ), f"Device {device_name} should have device_type"

    def test_groups_loading_from_real_config(self):
        """Test that groups are loaded from the real config files."""
        config_dir = Path("config")
        if not config_dir.exists():
            pytest.skip("Config directory not found")

        config = load_config(config_dir)

        # Check that we loaded groups from the actual group files
        group_files = list((config_dir / "groups").glob("*.yml"))
        if group_files:
            assert config.device_groups is not None, "Should load groups"
            assert len(config.device_groups) > 0, "Should load groups from group files"

    def test_config_loading_robustness(self):
        """Test that config loading is robust and handles missing vendor_platforms gracefully."""
        config_dir = Path("config")
        if not config_dir.exists():
            pytest.skip("Config directory not found")

        # Load config and verify it doesn't crash without vendor_platforms
        config = load_config(config_dir)

        # Should work even without explicit vendor_platforms configuration
        assert config is not None, "Config loading should not crash"

        # Should auto-discover vendor sequences as fallback
        sequences_dir = config_dir / "sequences"
        if sequences_dir.exists() and any(
            d.is_dir() for d in sequences_dir.iterdir() if not d.name.startswith(".")
        ):
            assert (
                config.vendor_sequences is not None
            ), "Should auto-discover vendor sequences"
            assert len(config.vendor_sequences) > 0, "Should find vendor sequences"
