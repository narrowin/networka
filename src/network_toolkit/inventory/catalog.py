# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Inventory catalog for multiple additive sources.

This module keeps track of devices and groups across multiple inventory sources
without forcing uniqueness at load time. Target resolution can then detect
ambiguity and optionally select a preferred source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from network_toolkit.config import DeviceConfig, DeviceGroup, NetworkConfig


@dataclass(frozen=True, slots=True)
class InventorySourceRef:
    """Metadata for an inventory source."""

    source_id: str
    kind: str
    root: Path | None = None
    inventory_file: Path | None = None


@dataclass(frozen=True, slots=True)
class DeviceEntry:
    name: str
    device: DeviceConfig
    ref: InventorySourceRef


@dataclass(frozen=True, slots=True)
class GroupEntry:
    name: str
    group: DeviceGroup
    ref: InventorySourceRef


def get_inventory_catalog(config: NetworkConfig) -> InventoryCatalog | None:
    """Return inventory catalog attached to a config, if present."""
    catalog = getattr(config, "_inventory_catalog", None)
    return catalog if isinstance(catalog, InventoryCatalog) else None


def set_inventory_catalog(config: NetworkConfig, catalog: InventoryCatalog) -> None:
    """Attach an inventory catalog to a config."""
    config._inventory_catalog = catalog


@dataclass
class InventoryCatalog:
    """Index devices and groups across multiple sources."""

    devices_by_name: dict[str, list[DeviceEntry]] = field(default_factory=dict)
    groups_by_name: dict[str, list[GroupEntry]] = field(default_factory=dict)
    sources: dict[str, InventorySourceRef] = field(default_factory=dict)

    def add_source(
        self,
        *,
        source_id: str,
        kind: str,
        root: Path | None,
        inventory_file: Path | None,
        devices: dict[str, Any],
        groups: dict[str, Any],
    ) -> None:
        ref = InventorySourceRef(
            source_id=source_id,
            kind=kind,
            root=root,
            inventory_file=inventory_file,
        )
        self.sources[source_id] = ref

        for name, dev in devices.items():
            entry = DeviceEntry(name=name, device=dev, ref=ref)
            self.devices_by_name.setdefault(name, []).append(entry)

        for name, grp in groups.items():
            grp_entry = GroupEntry(name=name, group=grp, ref=ref)
            self.groups_by_name.setdefault(name, []).append(grp_entry)

    def list_device_entries(self) -> list[DeviceEntry]:
        out: list[DeviceEntry] = []
        for entries in self.devices_by_name.values():
            out.extend(entries)
        return out

    def list_group_entries(self) -> list[GroupEntry]:
        out: list[GroupEntry] = []
        for entries in self.groups_by_name.values():
            out.extend(entries)
        return out

    def resolve_device(
        self, name: str, *, prefer: str | None = None, source_id: str | None = None
    ) -> DeviceEntry | None:
        entries = self.devices_by_name.get(name, [])
        return self._resolve_one(entries, name, prefer=prefer, source_id=source_id)

    def resolve_group(
        self, name: str, *, prefer: str | None = None, source_id: str | None = None
    ) -> GroupEntry | None:
        entries = self.groups_by_name.get(name, [])
        return self._resolve_one(entries, name, prefer=prefer, source_id=source_id)

    def _resolve_one(
        self,
        entries: list[Any],
        name: str,
        *,
        prefer: str | None,
        source_id: str | None,
    ) -> Any | None:
        if not entries:
            return None

        if source_id is not None:
            filtered = [e for e in entries if e.ref.source_id == source_id]
            if not filtered:
                return None
            if len(filtered) == 1:
                return filtered[0]
            # Source ids are supposed to be unique; treat duplicates as ambiguous.
            msg = f"Ambiguous inventory selection for '{name}' in source '{source_id}'"
            raise NetworkToolkitError(
                msg,
                details={
                    "name": name,
                    "source_id": source_id,
                    "candidates": [e.ref.source_id for e in filtered],
                },
            )

        if len(entries) == 1:
            return entries[0]

        if prefer:
            matches = [e for e in entries if _prefer_matches(prefer, e.ref)]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                msg = f"Inventory preference '{prefer}' matches multiple candidates for '{name}'"
                raise NetworkToolkitError(
                    msg,
                    details={
                        "name": name,
                        "prefer": prefer,
                        "candidates": [e.ref.source_id for e in matches],
                    },
                )

        msg = f"Ambiguous target '{name}' found in multiple inventories"
        raise NetworkToolkitError(
            msg,
            details={
                "name": name,
                "prefer": prefer,
                "candidates": [e.ref.source_id for e in entries],
            },
        )


def _prefer_matches(prefer: str, ref: InventorySourceRef) -> bool:
    p = prefer.strip()
    if not p:
        return False

    if p.lower() == "config":
        return ref.source_id == "config"

    if _matches_prefixed_source(p, ref):
        return True

    if p == ref.source_id:
        return True

    if not _looks_like_path(p):
        return False

    prefer_path = _resolve_prefer_path(p)
    if prefer_path is None:
        return False

    for candidate in (ref.root, ref.inventory_file):
        if candidate is None:
            continue
        try:
            if candidate.resolve() == prefer_path:
                return True
        except Exception:
            if candidate == prefer_path:
                return True
    return False


def _matches_prefixed_source(token: str, ref: InventorySourceRef) -> bool:
    """Match tokens like 'cli:inv1' or 'local:clab-s3n' against a source ref."""
    if ":" not in token:
        return False

    prefix_raw, source_id_raw = token.split(":", 1)
    prefix = prefix_raw.strip().lower()
    source_id = source_id_raw.strip()
    if not prefix or not source_id:
        return False

    if prefix == "local":
        prefix = "discovered"
    if prefix == "config":
        prefix = "config_inventory"

    if prefix == ref.kind.lower() and source_id == ref.source_id:
        return True

    # Allow explicit kind names as well.
    if prefix == "config_inventory" and ref.kind == "config_inventory":
        return source_id == ref.source_id
    if prefix == "discovered" and ref.kind == "discovered":
        return source_id == ref.source_id
    if prefix == "cli" and ref.kind == "cli":
        return source_id == ref.source_id
    if prefix == "config" and ref.kind == "config":
        return source_id == ref.source_id

    return False


def _looks_like_path(value: str) -> bool:
    if value.startswith((".", "~")):
        return True
    if value.startswith(("/", "\\")):
        return True
    return "/" in value or "\\" in value


def _resolve_prefer_path(value: str) -> Path | None:
    try:
        p = Path(value).expanduser()
    except Exception:
        return None
    try:
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
    except Exception:
        return None
    return p
