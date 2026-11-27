"""Unified Sequence Manager for built-in, repo, and user-defined sequences.

This module provides a single place to discover and resolve sequences:
- Built-in sequences shipped inside the package (src/network_toolkit/builtin_sequences)
- Repo-provided vendor sequences under config/sequences/<vendor>/*.yml
- User-defined sequences under ~/.config/networka/sequences/<vendor>/*.yml
- Custom user sequences under ~/.config/networka/sequences/custom/*.yml

Resolution order (highest wins):
1. Custom user sequences (sequences/custom/*.yml) - highest precedence
2. User-defined vendor sequences (sequences/<vendor>/*.yml)
3. Repo-provided vendor sequences from config/
4. Built-in sequences shipped with the package
5. Inline commands on the selected device
6. Global configuration sequences
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from network_toolkit.common.paths import user_sequences_dir
from network_toolkit.config import (
    NetworkConfig,
    VendorSequence,
    load_vendor_sequence_file,
)
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.catalog import get_inventory_catalog


@dataclass(frozen=True)
class SequenceSource:
    origin: str
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
    vendor: str | None = None
    device: str | None = None


class SequenceManager:
    """Select applicable sequence definitions with their winning source."""

    def __init__(self, config: NetworkConfig) -> None:
        self.config = config
        # Layered stores: builtin < repo < user < custom
        self._builtin: dict[str, dict[str, SequenceRecord]] = {}
        self._user: dict[str, dict[str, SequenceRecord]] = {}
        self._custom: dict[str, dict[str, SequenceRecord]] = {}
        # Preload from known places
        self._load_all()

    def _vendors(self) -> set[str]:
        return (set(self._builtin) | set(self._user) | set(self._custom)) | set(
            self.config.vendor_sequences or {}
        )

    def _vendor_records(self, vendor: str) -> dict[str, SequenceRecord]:
        configured = {
            name: self._record_from_vendor_sequence(name, seq, origin="repo")
            for name, seq in (self.config.vendor_sequences or {})
            .get(vendor, {})
            .items()
        }
        return {
            **self._builtin.get(vendor, {}),
            **configured,
            **self._user.get(vendor, {}),
            **self._custom.get(vendor, {}),
        }

    @staticmethod
    def _applies(record: SequenceRecord, vendor: str | None) -> bool:
        if not record.commands:
            return False
        types = record.device_types
        return types is None or (bool(types) and (vendor is None or vendor in types))

    def list_vendor_sequences(self, vendor: str) -> dict[str, SequenceRecord]:
        """Return applicable vendor definitions after whole-record precedence."""
        return {
            name: replace(record, vendor=vendor)
            for name, record in self._vendor_records(vendor).items()
            if self._applies(record, vendor)
        }

    def list_all_sequences(self) -> dict[str, dict[str, SequenceRecord]]:
        """Return applicable definitions under each configured or packaged vendor."""
        return {
            vendor: self.list_vendor_sequences(vendor)
            for vendor in sorted(self._vendors())
        }

    def list_global_sequences(
        self, vendor: str | None = None
    ) -> dict[str, SequenceRecord]:
        """Return global definitions, filtered when a vendor is selected."""
        records = {
            name: self._record_from_vendor_sequence(name, seq, origin="global")
            for name, seq in (self.config.global_command_sequences or {}).items()
        }
        return {
            name: record
            for name, record in records.items()
            if self._applies(record, vendor)
        }

    def list_platform_sequences(self, vendor: str) -> dict[str, SequenceRecord]:
        """Return winners for a platform without device-local context."""
        return {
            **self.list_global_sequences(vendor),
            **self.list_vendor_sequences(vendor),
        }

    def list_device_sequences(self, device_name: str) -> dict[str, SequenceRecord]:
        """Return the exact applicable winners for a selected inventory device."""
        device = (self.config.devices or {}).get(device_name)
        if device is None:
            return {}
        source = SequenceSource(
            "device", self.config.get_device_sequence_source_path(device_name)
        )
        inline = {
            name: SequenceRecord(
                name=name, commands=commands, source=source, device=device_name
            )
            for name, commands in (device.command_sequences or {}).items()
            if commands
        }
        return {
            **self.list_global_sequences(device.device_type),
            **inline,
            **self.list_vendor_sequences(device.device_type),
        }

    def catalog_records(self) -> list[SequenceRecord]:
        """List global fallbacks, vendor winners, and effective device-local records."""
        records = list(self.list_global_sequences().values())
        for sequences in self.list_all_sequences().values():
            records.extend(sequences.values())
        for device_name in sorted(self.config.devices or {}):
            records.extend(
                record
                for record in self.list_device_sequences(device_name).values()
                if record.device is not None
            )
        return records

    def known_names(self) -> set[str]:
        """Recognize configured names independently of execution eligibility."""
        names = set(self.config.global_command_sequences or {})
        for vendor in self._vendors():
            names.update(self._vendor_records(vendor))
        for device in (self.config.devices or {}).values():
            names.update(device.command_sequences or {})
        if catalog := get_inventory_catalog(self.config):
            for entries in catalog.devices_by_name.values():
                for entry in entries:
                    names.update(entry.device.command_sequences or {})
        return names

    def resolve(
        self, sequence_name: str, device_name: str | None = None
    ) -> list[str] | None:
        """Return commands from the winning record for the requested device."""
        record = (
            self.list_device_sequences(device_name).get(sequence_name)
            if device_name
            else None
        )
        return list(record.commands) if record is not None else None

    def exists(self, sequence_name: str) -> bool:
        """Recognize sequence names even when they do not apply to a target."""
        return sequence_name in self.known_names()

    def require(self, sequence_name: str, device_name: str) -> list[str]:
        """Resolve a nonempty sequence or stop the requested operation."""
        commands = self.resolve(sequence_name, device_name)
        if not commands:
            msg = f"Sequence '{sequence_name}' is not defined for '{device_name}'"
            raise NetworkToolkitError(msg)
        return commands

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
        """Load filename-scoped custom files and definitions for known platforms."""
        data: dict[str, dict[str, SequenceRecord]] = {}
        platforms = (
            self._vendors()
            | {device.device_type for device in (self.config.devices or {}).values()}
            | set(self.config.vendor_platforms or {})
        )
        if catalog := get_inventory_catalog(self.config):
            platforms.update(
                entry.device.device_type
                for entries in catalog.devices_by_name.values()
                for entry in entries
            )
        for path in sorted([*custom_root.glob("*.yml"), *custom_root.glob("*.yaml")]):
            sequences = self._load_yaml_sequences(path, origin="custom")
            declared = {
                platform
                for record in sequences.values()
                for platform in record.device_types or []
            }
            known_platforms = platforms | declared
            filename_platform = next(
                (
                    platform
                    for platform in sorted(known_platforms, key=len, reverse=True)
                    if path.stem.startswith(platform)
                ),
                None,
            )
            for name, record in sequences.items():
                targets = (
                    [filename_platform]
                    if filename_platform
                    else record.device_types or platforms
                )
                for platform in targets:
                    data.setdefault(platform, {})[name] = record
        return data

    def _load_from_root(
        self, root: Path, *, origin: str
    ) -> dict[str, dict[str, SequenceRecord]]:
        data: dict[str, dict[str, SequenceRecord]] = {}
        if not root.exists():
            return data
        for vendor_dir in root.iterdir():
            if (
                not vendor_dir.is_dir()
                or vendor_dir.name.startswith(".")
                or vendor_dir.name == "custom"
            ):
                continue
            vendor_name = vendor_dir.name
            vendor_map: dict[str, SequenceRecord] = {}
            for yml in sorted([*vendor_dir.glob("*.yml"), *vendor_dir.glob("*.yaml")]):
                vendor_map.update(self._load_yaml_sequences(yml, origin=origin))
            if vendor_map:
                data[vendor_name] = vendor_map
        return data

    def _load_yaml_sequences(
        self, path: Path, *, origin: str
    ) -> dict[str, SequenceRecord]:
        return {
            name: self._record_from_vendor_sequence(name, sequence, origin=origin)
            for name, sequence in load_vendor_sequence_file(path).items()
        }

    def _record_from_vendor_sequence(
        self, name: str, vseq: VendorSequence, *, origin: str
    ) -> SequenceRecord:
        return SequenceRecord(
            name=name,
            commands=list(vseq.commands),
            description=vseq.description or None,
            category=vseq.category,
            timeout=vseq.timeout,
            device_types=vseq.device_types,
            source=SequenceSource(origin=origin, path=vseq._source_path),
        )
