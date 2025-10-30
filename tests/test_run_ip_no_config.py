"""Test create_minimal_config function for IP-based commands without config directory.

This tests the fix for: nw run --platform mikrotik_routeros 10.99.1.21 "/cmd" --interactive-auth
failing with FileNotFoundError when ~/.config/networka/ doesn't exist.

The fix adds create_minimal_config() which creates a minimal NetworkConfig without requiring
config files on the filesystem.
"""

from network_toolkit.config import NetworkConfig, create_minimal_config


class TestMinimalConfig:
    """Test the create_minimal_config function used for IP-only mode."""

    def test_create_minimal_config_returns_valid_config(self) -> None:
        """Test that create_minimal_config returns a valid NetworkConfig."""
        config = create_minimal_config()

        assert isinstance(config, NetworkConfig)
        assert config.general is not None
        assert config.devices is None
        assert config.device_groups is None

    def test_minimal_config_has_required_defaults(self) -> None:
        """Test that minimal config has required default settings."""
        config = create_minimal_config()

        # Should have default transport type
        assert config.general.default_transport_type == "scrapli"

        # Should have default directories
        assert config.general.results_dir == "/tmp/results"
        assert config.general.backup_dir == "/tmp/backups"

        # Should have reasonable timeouts
        assert config.general.timeout == 30
        assert config.general.command_timeout == 60

    def test_minimal_config_works_without_filesystem(self) -> None:
        """Test that minimal config can be created without any config files."""
        # Create config without accessing filesystem
        config = create_minimal_config()

        # Should succeed without accessing filesystem
        assert config is not None
        assert hasattr(config, "general")

    def test_minimal_config_can_be_created_multiple_times(self) -> None:
        """Test that minimal config can be created multiple times independently."""
        config1 = create_minimal_config()
        config2 = create_minimal_config()

        # Should be separate instances
        assert config1 is not config2

        # But should have same defaults
        assert (
            config1.general.default_transport_type
            == config2.general.default_transport_type
        )
