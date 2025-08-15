"""Data access layer for the TUI.

This module isolates interactions with the existing codebase so the
Textual UI remains a thin layer on top.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.sequence_manager import SequenceManager


@dataclass(frozen=True)
class Targets:
    """Lists of available targets."""

    devices: list[str]
    groups: list[str]


@dataclass(frozen=True)
class Actions:
    """Lists of available actions to run."""

    sequences: list[str]
    # Free-form commands are user provided, not discovered here


class TuiData:
    """Load and expose configuration data for the TUI.

    Contract:
    - targets() -> Targets
    - actions() -> Actions
    - sequence_commands(name) -> list[str] | None
    """

    def __init__(self, config_path: str | Path = "devices.yml") -> None:
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
        cfg = load_config(self._config_path)
        self._config = cfg
        self._seq_mgr = SequenceManager(cfg)

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
