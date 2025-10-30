"""Unified Sequence Manager for built-in and user-defined sequences.

This module provides a single place to discover and resolve sequences:
- Built-in sequences shipped inside the package (src/network_toolkit/builtin_sequences)
- User-defined sequences under ~/.config/networka/sequences/<vendor>/*.yml
- Custom user sequences under ~/.config/networka/sequences/custom/*.yml

Resolution order (highest wins):
1. Custom user sequences (sequences/custom/*.yml) - highest precedence
2. User-defined vendor sequences (sequences/<vendor>/*.yml)
3. Built-in sequences shipped with the package
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from network_toolkit.common.paths import user_sequences_dir
from network_toolkit.config import NetworkConfig, VendorSequence


@dataclass(frozen=True)
class SequenceSource:
    origin: str  # "builtin" | "repo" | "user" | "custom"
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

    Resolution order (highest to lowest precedence):
    1. Custom user sequences (sequences/custom/*.yml)
    2. User vendor sequences (sequences/<vendor>/*.yml)
    3. Built-in sequences (package builtin_sequences/)

    Contract:
    - list_vendor_sequences(vendor) -> dict[str, SequenceRecord]
    - resolve(device_name, sequence_name) -> list[str] | None
    """

    def __init__(self, config: NetworkConfig) -> None:
        self.config = config
        # Layered stores: builtin < user < custom
        self._builtin: dict[str, dict[str, SequenceRecord]] = {}
        self._user: dict[str, dict[str, SequenceRecord]] = {}
        self._custom: dict[str, dict[str, SequenceRecord]] = {}
        # Preload from known places
        self._load_all()

    # ---------- Public API ----------
    def list_vendor_sequences(self, vendor: str) -> dict[str, SequenceRecord]:
        """Get merged sequences for a vendor (custom > user > builtin)."""
        merged: dict[str, SequenceRecord] = {}
        for layer in (
            self._builtin.get(vendor, {}),
            self._user.get(vendor, {}),
            self._custom.get(vendor, {}),  # Custom has highest precedence
        ):
            for name, rec in layer.items():
                merged[name] = rec
        # Also include config.vendor_sequences from NetworkConfig as lowest precedence
        if self.config.vendor_sequences and vendor in self.config.vendor_sequences:
            for name, vseq in self.config.vendor_sequences[vendor].items():
                # Only add if not already in merged (respect precedence)
                if name not in merged:
                    merged[name] = self._record_from_vendor_sequence(
                        name, vseq, origin="config", path=None
                    )
        return merged

    def list_all_sequences(self) -> dict[str, dict[str, SequenceRecord]]:
        """Return all vendors and their sequences (merged)."""
        vendors: set[str] = set(self._builtin) | set(self._user) | set(self._custom)
        if self.config.vendor_sequences:
            vendors |= set(self.config.vendor_sequences)
        return {v: self.list_vendor_sequences(v) for v in sorted(vendors)}

    def resolve(
        self, sequence_name: str, device_name: str | None = None
    ) -> list[str] | None:
        """Resolve a sequence to a list of commands with precedence.

        Order:
        1. Vendor sequences based on device_type via custom > user > builtin > config.vendor_sequences
        2. Device-specific sequences (legacy) via NetworkConfig
        """
        # 1. Vendor-based
        vendor = None
        if device_name and self.config.devices and device_name in self.config.devices:
            vendor = self.config.devices[device_name].device_type
        if vendor:
            merged = self.list_vendor_sequences(vendor)
            if sequence_name in merged:
                return list(merged[sequence_name].commands)

        # 2. Device-defined
        if self.config.devices:
            for dev in self.config.devices.values():
                if dev.command_sequences and sequence_name in dev.command_sequences:
                    return list(dev.command_sequences[sequence_name])
        return None

    def exists(self, sequence_name: str) -> bool:
        """Return True if a sequence is known anywhere (vendor or device)."""
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
        # User paths
        user_root = self._user_sequences_root()
        if user_root:
            self._user = self._load_from_root(user_root, origin="user")
        # Custom paths (highest precedence)
        custom_root = self._custom_sequences_root()
        if custom_root:
            self._custom = self._load_custom_sequences(custom_root)

    def _builtin_root(self) -> Path:
        # This file lives at src/network_toolkit/sequence_manager.py
        # builtin lives at src/network_toolkit/builtin_sequences
        return Path(__file__).parent / "builtin_sequences"

    def _user_sequences_root(self) -> Path | None:
        # Use OS-appropriate user config directory
        root = user_sequences_dir()
        return root if root.exists() else None

    def _custom_sequences_root(self) -> Path | None:
        """Get path to custom sequences directory.

        Custom sequences live in sequences/custom/ and have highest precedence.
        """
        root = user_sequences_dir()
        if root.exists():
            custom_dir = root / "custom"
            return custom_dir if custom_dir.exists() else None
        return None

    def _load_custom_sequences(
        self, custom_root: Path
    ) -> dict[str, dict[str, SequenceRecord]]:
        """Load custom sequences from sequences/custom/ directory.

        Custom sequences are organized by vendor name in the filename
        or loaded as vendor-agnostic and available to all vendors.
        """
        data: dict[str, dict[str, SequenceRecord]] = {}

        if not custom_root.exists():
            return data

        # Load all YAML files in custom/ directory
        for yml in sorted(custom_root.glob("*.yml")):
            sequences = self._load_yaml_sequences(yml, origin="custom")

            # Try to extract vendor from filename (e.g., mikrotik_custom.yml)
            # Otherwise make available to all known vendors
            filename_stem = yml.stem
            vendor_name = None

            # Check if filename starts with a known vendor platform
            for platform in [
                "mikrotik_routeros",
                "cisco_iosxe",
                "cisco_nxos",
                "arista_eos",
                "juniper_junos",
            ]:
                if filename_stem.startswith(platform):
                    vendor_name = platform
                    break

            if vendor_name:
                # Add to specific vendor
                if vendor_name not in data:
                    data[vendor_name] = {}
                data[vendor_name].update(sequences)
            else:
                # Make available to all vendors
                for vendor in [
                    "mikrotik_routeros",
                    "cisco_iosxe",
                    "cisco_nxos",
                    "arista_eos",
                    "juniper_junos",
                ]:
                    if vendor not in data:
                        data[vendor] = {}
                    data[vendor].update(sequences)

        return data

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
