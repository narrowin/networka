"""Unified Sequence Manager for built-in, repo, and user-defined sequences.

This module provides a single place to discover and resolve sequences:
- Built-in sequences shipped inside the package (src/network_toolkit/builtin_sequences)
- Repo-provided vendor sequences under config/sequences/<vendor>/*.yml
- User-defined sequences under ~/.config/netkit/sequences/<vendor>/*.yml

Resolution order (highest wins):
1. User-defined vendor sequences (override/extend)
2. Repo-provided vendor sequences from config/
3. Built-in sequences shipped with the package
4. Global sequences from config (NetworkConfig.global_command_sequences)

Global sequences remain available by name and are resolved before vendor/device ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from network_toolkit.config import NetworkConfig, VendorSequence


@dataclass(frozen=True)
class SequenceSource:
    origin: str  # "builtin" | "repo" | "user" | "global"
    path: Path | None


@dataclass
class SequenceRecord:
    name: str
    commands: list[str]
    description: str | None = None
    category: str | None = None
    timeout: int | None = None
    device_types: list[str] | None = None
    source: SequenceSource | None = None


class SequenceManager:
    """Loads and resolves sequences from multiple layers.

    Contract:
    - list_vendor_sequences(vendor) -> dict[str, SequenceRecord]
    - resolve(device_name, sequence_name) -> list[str] | None
    """

    def __init__(self, config: NetworkConfig) -> None:
        self.config = config
        # Layered stores: builtin < repo < user
        self._builtin: dict[str, dict[str, SequenceRecord]] = {}
        self._repo: dict[str, dict[str, SequenceRecord]] = {}
        self._user: dict[str, dict[str, SequenceRecord]] = {}
        # Preload from known places
        self._load_all()

    # ---------- Public API ----------
    def list_vendor_sequences(self, vendor: str) -> dict[str, SequenceRecord]:
        """Get merged sequences for a vendor (user > repo > builtin)."""
        merged: dict[str, SequenceRecord] = {}
        for layer in (
            self._builtin.get(vendor, {}),
            self._repo.get(vendor, {}),
            self._user.get(vendor, {}),
        ):
            for name, rec in layer.items():
                merged[name] = rec
        # Also include config.vendor_sequences from NetworkConfig as repo-level
        if self.config.vendor_sequences and vendor in self.config.vendor_sequences:
            for name, vseq in self.config.vendor_sequences[vendor].items():
                merged[name] = self._record_from_vendor_sequence(
                    name, vseq, origin="repo", path=None
                )
        return merged

    def list_all_sequences(self) -> dict[str, dict[str, SequenceRecord]]:
        """Return all vendors and their sequences (merged)."""
        vendors: set[str] = set(self._builtin) | set(self._repo) | set(self._user)
        if self.config.vendor_sequences:
            vendors |= set(self.config.vendor_sequences)
        return {v: self.list_vendor_sequences(v) for v in sorted(vendors)}

    def resolve(
        self, sequence_name: str, device_name: str | None = None
    ) -> list[str] | None:
        """Resolve a sequence to a list of commands with precedence.

        Order:
        1. Global sequences from config
        2. Vendor sequences based on device_type via user > repo > builtin > config.vendor_sequences
        3. Device-specific sequences (legacy) via NetworkConfig
        """
        # 1. Global
        if (
            self.config.global_command_sequences
            and sequence_name in self.config.global_command_sequences
        ):
            return list(self.config.global_command_sequences[sequence_name].commands)

        # 2. Vendor-based
        vendor = None
        if device_name and self.config.devices and device_name in self.config.devices:
            vendor = self.config.devices[device_name].device_type
        if vendor:
            merged = self.list_vendor_sequences(vendor)
            if sequence_name in merged:
                return list(merged[sequence_name].commands)

        # 3. Device-defined
        if self.config.devices:
            for dev in self.config.devices.values():
                if dev.command_sequences and sequence_name in dev.command_sequences:
                    return list(dev.command_sequences[sequence_name])
        return None

    def exists(self, sequence_name: str) -> bool:
        """Return True if a sequence is known anywhere (global, vendor, or device)."""
        if (
            self.config.global_command_sequences
            and sequence_name in self.config.global_command_sequences
        ):
            return True
        # Any vendor layer
        all_vendor = self.list_all_sequences()
        for vendor_map in all_vendor.values():
            if sequence_name in vendor_map:
                return True
        # Any device-defined
        if self.config.devices:
            for dev in self.config.devices.values():
                if dev.command_sequences and sequence_name in dev.command_sequences:
                    return True
        return False

    # ---------- Internal loading ----------
    def _load_all(self) -> None:
        self._builtin = self._load_from_root(self._builtin_root(), origin="builtin")
        # Repo paths from modular config
        repo_root = self._repo_sequences_root()
        if repo_root:
            self._repo = self._load_from_root(repo_root, origin="repo")
        # User paths
        user_root = self._user_sequences_root()
        if user_root:
            self._user = self._load_from_root(user_root, origin="user")

    def _builtin_root(self) -> Path:
        # This file lives at src/network_toolkit/sequence_manager.py
        # builtin lives at src/network_toolkit/builtin_sequences
        return Path(__file__).parent / "builtin_sequences"

    def _repo_sequences_root(self) -> Path | None:
        # Try to infer from config file structure:
        # config/vendor_platforms sequence_path is relative to config dir
        # We can discover one of the configured paths and take its parent as root.
        if not self.config or not self.config.vendor_platforms:
            return None
        # Heuristic: find any platform with sequence_path set and resolve
        # against a likely config dir. Assume run is invoked with load_config
        # pointing to a modular config dir; extract from first path.
        for platform in self.config.vendor_platforms.values():
            rel = platform.sequence_path
            # Find a directory that exists by walking up from CWD
            candidate = Path.cwd() / "config" / rel
            if candidate.exists():
                return candidate.parent
        return None

    def _user_sequences_root(self) -> Path | None:
        # XDG-style config: ~/.config/netkit/sequences
        root = Path.home() / ".config" / "netkit" / "sequences"
        return root if root.exists() else None

    def _load_from_root(
        self, root: Path, *, origin: str
    ) -> dict[str, dict[str, SequenceRecord]]:
        data: dict[str, dict[str, SequenceRecord]] = {}
        if not root.exists():
            return data
        for vendor_dir in root.iterdir():
            if not vendor_dir.is_dir():
                continue
            vendor_name = vendor_dir.name
            vendor_map: dict[str, SequenceRecord] = {}
            for yml in sorted(vendor_dir.glob("*.yml")):
                for name, rec in self._load_yaml_sequences(yml, origin=origin).items():
                    vendor_map[name] = rec
            if vendor_map:
                data[vendor_name] = vendor_map
        return data

    def _load_yaml_sequences(
        self, path: Path, *, origin: str
    ) -> dict[str, SequenceRecord]:
        try:
            with path.open("r", encoding="utf-8") as f:
                loaded: Any = yaml.safe_load(f)
                raw = cast(dict[str, Any], loaded or {})
        except Exception:
            return {}

        out: dict[str, SequenceRecord] = {}
        seqs_any: Any = raw.get("sequences", {}) or {}
        seqs = cast(dict[str, Any], seqs_any)
        for name_any, body_any in seqs.items():
            name = name_any
            body = cast(dict[str, Any], body_any or {})
            commands = list(cast(list[str], body.get("commands", []) or []))
            if not commands:
                continue
            out[name] = SequenceRecord(
                name=name,
                commands=commands,
                description=cast(str | None, body.get("description")),
                category=cast(str | None, body.get("category")),
                timeout=cast(int | None, body.get("timeout")),
                device_types=cast(list[str] | None, body.get("device_types")),
                source=SequenceSource(origin=origin, path=path),
            )
        return out

    def _record_from_vendor_sequence(
        self, name: str, vseq: VendorSequence, *, origin: str, path: Path | None
    ) -> SequenceRecord:
        return SequenceRecord(
            name=name,
            commands=list(vseq.commands),
            description=getattr(vseq, "description", None),
            category=getattr(vseq, "category", None),
            timeout=getattr(vseq, "timeout", None),
            device_types=getattr(vseq, "device_types", None),
            source=SequenceSource(origin=origin, path=path),
        )
