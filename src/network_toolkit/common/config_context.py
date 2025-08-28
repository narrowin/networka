# SPDX-License-Identifier: MIT
"""Centralized configuration context with lazy loading and intelligent path resolution."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from network_toolkit.common.paths import default_modular_config_dir
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.exceptions import ConfigurationError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConfigSourceInfo(BaseModel):
    """Information about where configuration was loaded from."""

    path: Path = Field(description="Absolute path to config source")
    source_type: str = Field(description="Type: explicit, project, global, default")
    is_fallback: bool = Field(
        default=False, description="Whether this was a fallback path"
    )

    model_config = {"arbitrary_types_allowed": True}

    def display_name(self) -> str:
        """Human-readable source description."""
        if self.source_type == "explicit":
            return f"Explicit path: {self.path}"
        elif self.source_type == "project":
            return f"Project config: {self.path}"
        elif self.source_type == "global":
            return f"Global config: {self.path}"
        else:
            return f"Default config: {self.path}"


class ConfigContext(BaseModel):
    """
    Centralized configuration context with lazy loading and intelligent path resolution.

    This class provides a single point of access for configuration loading across all commands.
    It implements lazy loading for performance and intelligent path resolution for user convenience.

    Uses Pydantic v2 for validation and clean interfaces.
    """

    # Input configuration
    config_path: Path = Field(
        default_factory=lambda: Path("config"), description="Config path to load"
    )
    # Private attributes for caching (Pydantic v2 style)
    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
    }

    def __init__(self, **data):
        super().__init__(**data)
        self._config: NetworkConfig | None = None
        self._source_info: ConfigSourceInfo | None = None
        self._load_attempted: bool = False

    @classmethod
    def from_path(cls, config_path: str | Path | None = None) -> ConfigContext:
        """
        Create ConfigContext with intelligent path resolution.

        Args:
            config_path: User-provided path, or None for default resolution

        Returns:
            ConfigContext ready for use
        """
        path = Path(config_path) if config_path else Path("config")
        return cls(config_path=path)

    @property
    def config(self) -> NetworkConfig:
        """Get configuration, loading it lazily if needed."""
        if self._config is None and not self._load_attempted:
            self._load_config()

        if self._config is None:
            msg = f"Configuration could not be loaded from {self.config_path}"
            raise ConfigurationError(msg, details={"path": str(self.config_path)})

        return self._config

    @property
    def source_info(self) -> ConfigSourceInfo | None:
        """Get information about configuration source."""
        return self._source_info

    def _resolve_config_path(self) -> tuple[Path, str]:
        """Resolve configuration path with intelligent fallbacks.

        Returns:
            Tuple of (resolved_path, source_type)
        """
        original_path = self.config_path

        # If user provided explicit path that exists, use it
        if (
            str(original_path) not in ["config", "devices.yml"]
            and original_path.exists()
        ):
            return original_path, "explicit"

        # Check current directory for project config
        if original_path.name == "config":
            # First try current directory
            if original_path.exists():
                return original_path, "project"

            # Try global config location
            global_config_dir = default_modular_config_dir()
            if (
                global_config_dir.exists()
                and (global_config_dir / "config.yml").exists()
            ):
                return global_config_dir, "global"

        # For other cases, try the path as-is first
        if original_path.exists():
            return original_path, "project"

        # Final fallback to global config
        global_config_dir = default_modular_config_dir()
        if global_config_dir.exists():
            return global_config_dir, "global"

        # If nothing found, return original path for error handling
        return original_path, "default"

    def _load_config(self) -> None:
        """Load configuration with error handling."""
        self._load_attempted = True

        try:
            resolved_path, source_type = self._resolve_config_path()

            logger.debug(f"Loading config from {resolved_path} (source: {source_type})")

            self._config = load_config(resolved_path)
            self._source_info = ConfigSourceInfo(
                path=resolved_path,
                source_type=source_type,
                is_fallback=(source_type in ["global", "default"]),
            )

            logger.debug(
                f"Successfully loaded config from {self._source_info.display_name}"
            )

        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            # Don't raise here - let the property access handle the error
            # This allows for better error messages with context

    def reload(self) -> None:
        """Force reload of configuration."""
        self._config = None
        self._source_info = None
        self._load_attempted = False

    def is_loaded(self) -> bool:
        """Check if configuration has been successfully loaded."""
        return self._config is not None

    def validate_target_exists(self, target: str) -> bool:
        """
        Check if a target (device/group/sequence) exists in configuration.

        Args:
            target: Target name to check

        Returns:
            True if target exists, False otherwise
        """
        config = self.config  # Triggers loading if needed

        # Check devices
        if config.devices and target in config.devices:
            return True

        # Check groups
        if config.device_groups and target in config.device_groups:
            return True

        # Check global sequences
        if (
            config.global_command_sequences
            and target in config.global_command_sequences
        ):
            return True

        # Check vendor sequences
        from network_toolkit.sequence_manager import SequenceManager

        sm = SequenceManager(config)
        all_sequences = sm.list_all_sequences()
        for vendor_sequences in all_sequences.values():
            if target in vendor_sequences:
                return True

        return False
        self._load_config()
