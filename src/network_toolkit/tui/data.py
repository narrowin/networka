"""Data access layer for the TUI.

This module isolates interactions with the existing codebase so the
Textual UI remains a thin layer on top.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict

from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.sequence_manager import SequenceManager


class Targets(BaseModel):
    """Lists of available targets."""

    model_config = ConfigDict(frozen=True)

    devices: list[str]
    groups: list[str]


class Actions(BaseModel):
    """Lists of available actions to run."""

    model_config = ConfigDict(frozen=True)

    sequences: list[str]
    # Free-form commands are user provided, not discovered here


class TuiData:
    """Load and expose configuration data for the TUI.

    Contract:
    - targets() -> Targets
    - actions() -> Actions
    - sequence_commands(name) -> list[str] | None
    """

    def __init__(self, config_path: str | Path = "config") -> None:
        self._config_path = Path(config_path)
        self._config: NetworkConfig | None = None
        self._seq_mgr: SequenceManager | None = None
        self._load()

    @property
    def config(self) -> NetworkConfig:
        assert self._config is not None
        return self._config

    @property
    def sequence_manager(self) -> SequenceManager:
        assert self._seq_mgr is not None
        return self._seq_mgr

    def _load(self) -> None:
        cfg_path = self._config_path
        try:
            cfg = load_config(cfg_path)
        except FileNotFoundError:
            fallback = self._resolve_fallback_config_path(cfg_path)
            if fallback is None:
                raise
            cfg = load_config(fallback)
            # Remember the resolved path for later
            self._config_path = fallback
        self._config = cfg
        self._seq_mgr = SequenceManager(cfg)

    def _resolve_fallback_config_path(self, original: Path) -> Path | None:
        """Best-effort fallback discovery for config directory.

        Attempts the following in order:
        1. NW_CONFIG_DIR environment variable
        2. Search upwards from current working directory for a 'config' directory
        3. Search upwards from this module's parent directories for a 'config' directory
        """
        # 1) Explicit environment override
        env_dir = os.environ.get("NW_CONFIG_DIR")
        if env_dir:
            p = Path(env_dir)
            if p.exists():
                return p

        # Function to search ancestors for a folder named 'config'
        def search_up(start: Path) -> Path | None:
            cur = start
            seen = 0
            while True:
                candidate = cur / "config"
                if candidate.exists() and candidate.is_dir():
                    return candidate
                if cur.parent == cur or seen > 10:
                    return None
                cur = cur.parent
                seen += 1

        # 2) From CWD
        cwd_found = search_up(Path.cwd())
        if cwd_found is not None:
            return cwd_found

        # 3) From this file location
        module_found = search_up(Path(__file__).resolve())
        if module_found is not None:
            return module_found

        return None

    def targets(self) -> Targets:
        devs = cast(dict[str, Any], self.config.devices or {})
        grps = cast(dict[str, Any], self.config.device_groups or {})
        devices: list[str] = sorted(devs.keys())
        groups: list[str] = sorted(grps.keys())
        return Targets(devices=devices, groups=groups)

    def actions(self) -> Actions:
        sequences = sorted(self._discover_all_sequences())
        return Actions(sequences=sequences)

    def _discover_all_sequences(self) -> Iterable[str]:
        names: set[str] = set()
        # Global
        if self.config.global_command_sequences:
            names |= set(self.config.global_command_sequences.keys())
        # Vendor via SequenceManager
        for vendor_map in self.sequence_manager.list_all_sequences().values():
            names |= set(vendor_map.keys())
        # Device-defined sequences
        if self.config.devices:
            for dev in self.config.devices.values():
                if dev.command_sequences:
                    names |= set(dev.command_sequences.keys())
        return names

    def sequence_commands(
        self, name: str, device_name: str | None = None
    ) -> list[str] | None:
        return self.sequence_manager.resolve(name, device_name)
