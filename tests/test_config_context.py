"""Tests for ConfigContext with Pydantic v2."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from network_toolkit.common.config_context import ConfigContext, ConfigSourceInfo
from network_toolkit.config import NetworkConfig
from network_toolkit.exceptions import ConfigurationError


class TestConfigSourceInfo:
    """Test ConfigSourceInfo Pydantic model."""

    def test_source_info_creation(self):
        """Test basic ConfigSourceInfo creation."""
        info = ConfigSourceInfo(
            path=Path("/test/config"), source_type="project", is_fallback=False
        )

        assert info.path == Path("/test/config")
        assert info.source_type == "project"
        assert not info.is_fallback

    def test_display_name_project(self):
        """Test display name for project config."""
        info = ConfigSourceInfo(
            path=Path("/project/config"), source_type="project", is_fallback=False
        )

        assert info.display_name() == "Project config: /project/config"

    def test_display_name_global(self):
        """Test display name for global config."""
        info = ConfigSourceInfo(
            path=Path("/home/.config/networka"), source_type="global", is_fallback=True
        )

        assert info.display_name() == "Global config: /home/.config/networka"


class TestConfigContext:
    """Test ConfigContext functionality."""

    def test_creation_default_path(self):
        """Test ConfigContext creation with default path."""
        ctx = ConfigContext()
        assert ctx.config_path == Path("config")

    def test_creation_explicit_path(self):
        """Test ConfigContext creation with explicit path."""
        ctx = ConfigContext(config_path=Path("/test/devices.yml"))
        assert ctx.config_path == Path("/test/devices.yml")

    def test_from_path_classmethod(self):
        """Test ConfigContext.from_path class method."""
        ctx = ConfigContext.from_path("/custom/config")
        assert ctx.config_path == Path("/custom/config")

        ctx_default = ConfigContext.from_path(None)
        assert ctx_default.config_path == Path("config")

    def test_is_loaded_initially_false(self):
        """Test that config is not loaded initially."""
        ctx = ConfigContext()
        assert not ctx.is_loaded()

    @patch("network_toolkit.common.config_context.load_config")
    def test_lazy_loading(self, mock_load_config):
        """Test that config is loaded lazily on first access."""
        mock_config = Mock(spec=NetworkConfig)
        mock_load_config.return_value = mock_config

        # Create a context that points to an existing file
        with patch("pathlib.Path.exists", return_value=True):
            ctx = ConfigContext(config_path=Path("test_config"))

            # Config should not be loaded yet
            assert not ctx.is_loaded()

            # Access config property should trigger loading
            config = ctx.config

            # Verify loading happened
            assert ctx.is_loaded()
            assert config is mock_config
            mock_load_config.assert_called_once()

    @patch("network_toolkit.common.config_context.load_config")
    def test_config_access_failure(self, mock_load_config):
        """Test config access when loading fails."""
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        ctx = ConfigContext(config_path=Path("nonexistent"))

        with pytest.raises(ConfigurationError) as exc_info:
            _ = ctx.config

        assert "Configuration could not be loaded" in str(exc_info.value)

    def test_reload_clears_cache(self):
        """Test that reload clears cached config."""
        ctx = ConfigContext()
        ctx._config = Mock(spec=NetworkConfig)
        ctx._load_attempted = True

        ctx.reload()

        assert ctx._config is None
        assert not ctx._load_attempted

    @patch("network_toolkit.common.config_context.load_config")
    def test_validate_target_exists_device(self, mock_load_config):
        """Test target validation for devices."""
        mock_config = Mock(spec=NetworkConfig)
        mock_config.devices = {"router1": Mock(), "switch1": Mock()}
        mock_config.device_groups = None
        mock_config.global_command_sequences = None
        mock_config.vendor_platforms = None  # Add missing attribute
        mock_config.vendor_sequences = None  # Add missing attribute
        mock_load_config.return_value = mock_config

        with patch("pathlib.Path.exists", return_value=True):
            ctx = ConfigContext(config_path=Path("test_config"))

            assert ctx.validate_target_exists("router1")
            assert not ctx.validate_target_exists("nonexistent")

    @patch("network_toolkit.common.config_context.load_config")
    def test_path_resolution_explicit(self, mock_load_config):
        """Test path resolution for explicit existing paths."""
        mock_config = Mock(spec=NetworkConfig)
        mock_load_config.return_value = mock_config

        with patch("pathlib.Path.exists", return_value=True):
            ctx = ConfigContext(config_path=Path("/explicit/path/config.yml"))
            resolved_path, source_type = ctx._resolve_config_path()

            assert resolved_path == Path("/explicit/path/config.yml")
            assert source_type == "explicit"

    @patch("network_toolkit.common.config_context.default_modular_config_dir")
    def test_path_resolution_fallback_to_global(self, mock_default_dir):
        """Test path resolution falling back to global config."""
        mock_default_dir.return_value = Path("/home/.config/networka")

        def mock_exists(self):
            return str(self).endswith(".config/networka")

        with patch("pathlib.Path.exists", mock_exists):
            ctx = ConfigContext(config_path=Path("config"))
            resolved_path, source_type = ctx._resolve_config_path()

            assert resolved_path == Path("/home/.config/networka")
            assert source_type == "global"
