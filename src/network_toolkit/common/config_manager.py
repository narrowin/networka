# SPDX-License-Identifier: MIT
"""Centralized configuration management for consistent config loading across all commands."""

from __future__ import annotations

import logging
from pathlib import Path

from network_toolkit.common.paths import default_modular_config_dir
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigManager:
    """Centralized configuration management with consistent error handling."""

    @staticmethod
    def resolve_config_path(config_path: str | Path) -> Path:
        """Resolve config path with intelligent fallback logic.

        Args:
            config_path: Path to config file or directory

        Returns:
            Resolved Path object
        """
        if isinstance(config_path, str):
            config_path = Path(config_path)

        # If explicit path exists, use it
        if config_path.exists():
            return config_path

        # If default names, try fallback locations
        if str(config_path) in ["config", "devices.yml"]:
            # Try platform default first
            platform_default = default_modular_config_dir()
            if (platform_default / "config.yml").exists():
                return platform_default

            # Try local config directory
            local_config = Path("config")
            if local_config.exists() and local_config.is_dir():
                return local_config

        # Return original path for proper error handling downstream
        return config_path

    @staticmethod
    def load_config_safe(config_path: str | Path) -> NetworkConfig:
        """Load configuration with consistent error handling.

        Args:
            config_path: Path to config file or directory

        Returns:
            Loaded NetworkConfig

        Raises:
            ConfigurationError: If config cannot be loaded
        """
        try:
            resolved_path = ConfigManager.resolve_config_path(config_path)
            logger.debug(f"Loading config from {resolved_path}")

            config = load_config(resolved_path)
            logger.debug(f"Successfully loaded config from {resolved_path}")

            return config

        except FileNotFoundError as e:
            msg = f"Configuration file not found: {config_path}"
            raise ConfigurationError(msg) from e
        except ValueError as e:
            msg = f"Invalid configuration: {e}"
            raise ConfigurationError(msg) from e
        except Exception as e:
            msg = f"Failed to load configuration from {config_path}: {e}"
            raise ConfigurationError(msg) from e
