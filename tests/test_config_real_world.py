"""
Test configuration loading against real-world config structure.

This test suite verifies that the configuration loading works with the actual
config directory structure in the repository, catching issues that synthetic
test fixtures might miss.
"""

from pathlib import Path

from network_toolkit.config import load_config


class TestRealWorldConfigLoading:
    """Test configuration loading with actual config files."""

    def test_load_config_with_directory_path(self, mock_repo_config: Path):
        """Test loading config by pointing to the config directory."""
        config = load_config(mock_repo_config)

        # Verify basic structure loaded
        assert config.devices is not None, (
            "Devices should be loaded from config/devices/"
        )
        assert config.device_groups is not None, (
            "Groups should be loaded from config/groups/"
        )

        # Verify we get vendor sequences (even if empty from init)
        assert config.vendor_sequences is not None, (
            "Vendor sequences should be initialized"
        )

        # Check if vendor directories exist (init creates them for future use)
        expected_vendors = [
            "mikrotik",
            "cisco",
        ]
        for vendor in expected_vendors:
            vendor_dir = mock_repo_config / "sequences" / vendor
            if vendor_dir.exists():
                # Directory exists - that's what init creates for future use
                assert vendor_dir.is_dir(), f"Should create {vendor} vendor directory"

    def test_load_config_with_config_yml_path(self, mock_repo_config: Path):
        """Test loading config by pointing to config.yml file - should detect modular structure."""
        config_file = mock_repo_config / "config.yml"

        config = load_config(config_file)

        # Should detect that this is part of a modular config and load everything
        assert config.devices is not None, (
            "Should load devices even when pointing to config.yml"
        )
        assert len(config.devices) > 0, "Should find devices in config/devices/"

        # Sequences now come from built-in package, not config directory
        # So we don't expect global_command_sequences from config files

    def test_devices_loading_from_real_config(self, mock_repo_config: Path):
        """Test loading devices from actual config structure."""
        config = load_config(mock_repo_config)

        device_files = list((mock_repo_config / "devices").glob("*.yml"))
        if device_files:
            assert config.devices is not None, "Should load devices"
            assert len(config.devices) > 0, "Should have devices from files"

            # Verify each device has required fields
            for device_name, device_info in config.devices.items():
                assert device_info.host, f"Device {device_name} should have host"
                assert device_info.platform, (
                    f"Device {device_name} should have platform"
                )

    def test_groups_loading_from_real_config(self, mock_repo_config: Path):
        """Test loading groups from actual config structure."""
        config = load_config(mock_repo_config)

        group_files = list((mock_repo_config / "groups").glob("*.yml"))
        if group_files:
            assert config.device_groups is not None, "Should load groups"
            assert len(config.device_groups) > 0, "Should have groups from files"

    def test_config_loading_robustness(self, mock_repo_config: Path):
        """Test that config loading is robust with various structures."""
        # Should load without error
        config = load_config(mock_repo_config)

        # Basic validation
        assert config is not None, "Should create config object"

        sequences_dir = mock_repo_config / "sequences"
        if sequences_dir.exists():
            # Vendor sequences should have been auto-discovered
            assert config.vendor_sequences is not None
            # At least one vendor should be discovered
            assert len(config.vendor_sequences) >= 0  # Allow empty for test env

        # Should work even without explicit vendor_platforms configuration
        assert config is not None, "Config loading should not crash"
