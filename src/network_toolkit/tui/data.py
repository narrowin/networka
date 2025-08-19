"""Enhanced data access layer for the TUI.

This module provides a modern, async-capable data service that isolates
TUI components from the core configuration and sequence management systems.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict

from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.sequence_manager import SequenceManager


class TargetData(BaseModel):
    """Available target devices and groups."""

    model_config = ConfigDict(frozen=True)

    devices: list[str]
    groups: list[str]


class ActionData(BaseModel):
    """Available actions (sequences) that can be executed."""

    model_config = ConfigDict(frozen=True)

    sequences: list[str]


class TuiDataService:
    """Modern async data service for TUI components.

    Provides clean, async access to configuration data with caching
    and error handling for better TUI responsiveness.
    """

    def __init__(self, config_path: str | Path = "config") -> None:
        """Initialize the data service.

        Args:
            config_path: Path to configuration directory or file
        """
        self._config_path = Path(config_path)
        self._config: NetworkConfig | None = None
        self._seq_mgr: SequenceManager | None = None
        self._loaded = False

        # Cached data
        self._targets: TargetData | None = None
        self._actions: ActionData | None = None

    @property
    def config(self) -> NetworkConfig:
        """Get the loaded configuration.

        Raises:
            RuntimeError: If configuration is not loaded
        """
        if self._config is None:
            msg = "Configuration not loaded. Call load_data() first."
            raise RuntimeError(msg)
        return self._config

    @property
    def sequence_manager(self) -> SequenceManager:
        """Get the sequence manager.

        Raises:
            RuntimeError: If configuration is not loaded
        """
        if self._seq_mgr is None:
            msg = "Configuration not loaded. Call load_data() first."
            raise RuntimeError(msg)
        return self._seq_mgr

    async def load_data(self) -> None:
        """Load configuration and initialize managers asynchronously."""
        if self._loaded:
            return

        try:
            # Load configuration in thread pool to avoid blocking UI
            config = await asyncio.to_thread(self._load_config)
            self._config = config
            self._seq_mgr = SequenceManager(config)

            # Pre-cache commonly accessed data
            await self._refresh_cache()

            self._loaded = True

        except Exception as e:
            msg = f"Failed to load configuration: {e}"
            raise RuntimeError(msg) from e

    def _load_config(self) -> NetworkConfig:
        """Load configuration with fallback discovery."""
        cfg_path = self._config_path
        try:
            return load_config(cfg_path)
        except FileNotFoundError:
            fallback = self._resolve_fallback_config_path(cfg_path)
            if fallback is None:
                raise
            # Update path to resolved fallback
            self._config_path = fallback
            return load_config(fallback)

    def _resolve_fallback_config_path(self, original: Path) -> Path | None:
        """Discover fallback configuration paths.

        Search order:
        1. NW_CONFIG_DIR environment variable
        2. Search upward from current directory for 'config' folder
        3. Search upward from module location for 'config' folder
        """
        # Environment override
        env_dir = os.environ.get("NW_CONFIG_DIR")
        if env_dir:
            p = Path(env_dir)
            if p.exists():
                return p

        def search_upward(start: Path) -> Path | None:
            """Search ancestor directories for 'config' folder."""
            current = start
            for _ in range(10):  # Limit search depth
                candidate = current / "config"
                if candidate.exists() and candidate.is_dir():
                    return candidate
                if current.parent == current:  # Reached root
                    break
                current = current.parent
            return None

        # Search from current working directory
        cwd_result = search_upward(Path.cwd())
        if cwd_result:
            return cwd_result

        # Search from module location
        module_result = search_upward(Path(__file__).resolve())
        if module_result:
            return module_result

        return None

    async def _refresh_cache(self) -> None:
        """Refresh cached data."""
        # Run data collection in thread pool
        targets_data, actions_data = await asyncio.gather(
            asyncio.to_thread(self._collect_targets),
            asyncio.to_thread(self._collect_actions),
        )

        self._targets = targets_data
        self._actions = actions_data

    def _collect_targets(self) -> TargetData:
        """Collect available devices and groups."""
        devices_dict = cast(dict[str, Any], self.config.devices or {})
        groups_dict = cast(dict[str, Any], self.config.device_groups or {})

        devices = sorted(devices_dict.keys())
        groups = sorted(groups_dict.keys())

        return TargetData(devices=devices, groups=groups)

    def _collect_actions(self) -> ActionData:
        """Collect available sequences."""
        sequences = sorted(self._discover_all_sequences())
        return ActionData(sequences=sequences)

    def _discover_all_sequences(self) -> set[str]:
        """Discover all available sequence names."""
        names: set[str] = set()

        # Global sequences
        if self.config.global_command_sequences:
            names.update(self.config.global_command_sequences.keys())

        # Vendor sequences via SequenceManager
        for vendor_map in self.sequence_manager.list_all_sequences().values():
            names.update(vendor_map.keys())

        # Device-specific sequences
        if self.config.devices:
            for device in self.config.devices.values():
                if device.command_sequences:
                    names.update(device.command_sequences.keys())

        return names

    async def get_targets(self) -> TargetData:
        """Get available targets (devices and groups).

        Returns:
            Target data with sorted lists
        """
        if not self._loaded:
            await self.load_data()

        if self._targets is None:
            await self._refresh_cache()

        return self._targets  # type: ignore[return-value]

    async def get_actions(self) -> ActionData:
        """Get available actions (sequences).

        Returns:
            Action data with sorted sequences
        """
        if not self._loaded:
            await self.load_data()

        if self._actions is None:
            await self._refresh_cache()

        return self._actions  # type: ignore[return-value]

    async def resolve_sequence_commands(
        self, sequence_name: str, device_name: str | None = None
    ) -> list[str] | None:
        """Resolve sequence to commands for a specific device.

        Args:
            sequence_name: Name of the sequence to resolve
            device_name: Target device name for context

        Returns:
            List of commands or None if sequence not found
        """
        if not self._loaded:
            await self.load_data()

        # Run resolution in thread pool to avoid blocking
        return await asyncio.to_thread(
            self.sequence_manager.resolve, sequence_name, device_name
        )

    async def filter_targets(
        self, device_filter: str = "", group_filter: str = ""
    ) -> TargetData:
        """Get filtered targets.

        Args:
            device_filter: Filter string for devices
            group_filter: Filter string for groups

        Returns:
            Filtered target data
        """
        targets = await self.get_targets()

        # Filter devices
        filtered_devices = targets.devices
        if device_filter:
            filter_lower = device_filter.lower()
            filtered_devices = [
                device for device in targets.devices if filter_lower in device.lower()
            ]

        # Filter groups
        filtered_groups = targets.groups
        if group_filter:
            filter_lower = group_filter.lower()
            filtered_groups = [
                group for group in targets.groups if filter_lower in group.lower()
            ]

        return TargetData(devices=filtered_devices, groups=filtered_groups)

    async def filter_actions(self, sequence_filter: str = "") -> ActionData:
        """Get filtered actions.

        Args:
            sequence_filter: Filter string for sequences

        Returns:
            Filtered action data
        """
        actions = await self.get_actions()

        if not sequence_filter:
            return actions

        filter_lower = sequence_filter.lower()
        filtered_sequences = [
            seq for seq in actions.sequences if filter_lower in seq.lower()
        ]

        return ActionData(sequences=filtered_sequences)


# Legacy compatibility - keep the original TuiData class for existing tests
class TuiData:
    """Legacy data access class for backward compatibility."""

    def __init__(self, config_path: str | Path = "config") -> None:
        self._service = TuiDataService(config_path)
        # Force synchronous loading for legacy compatibility
        asyncio.run(self._service.load_data())

    @property
    def config(self) -> NetworkConfig:
        return self._service.config

    @property
    def sequence_manager(self) -> SequenceManager:
        return self._service.sequence_manager

    def targets(self) -> Targets:
        """Get targets using legacy format."""
        data = asyncio.run(self._service.get_targets())
        return Targets(devices=data.devices, groups=data.groups)

    def actions(self) -> Actions:
        """Get actions using legacy format."""
        data = asyncio.run(self._service.get_actions())
        return Actions(sequences=data.sequences)

    def sequence_commands(
        self, name: str, device_name: str | None = None
    ) -> list[str] | None:
        """Get sequence commands using legacy format."""
        return asyncio.run(self._service.resolve_sequence_commands(name, device_name))


# Legacy model classes for backward compatibility
class Targets(BaseModel):
    """Legacy targets model."""

    model_config = ConfigDict(frozen=True)
    devices: list[str]
    groups: list[str]


class Actions(BaseModel):
    """Legacy actions model."""

    model_config = ConfigDict(frozen=True)
    sequences: list[str]
