"""Programmatic API for list operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from network_toolkit.config import NetworkConfig
from network_toolkit.inventory.catalog import get_inventory_catalog
from network_toolkit.sequence_manager import SequenceManager, SequenceRecord


@dataclass
class DeviceInfo:
    """Information about a device."""

    name: str
    hostname: str
    device_type: str
    transport: str
    groups: list[str]
    description: str | None = None
    tags: list[str] | None = None
    source: str | None = None


@dataclass
class GroupInfo:
    """Information about a group."""

    name: str
    members: list[str]
    description: str | None = None
    match_tags: list[str] | None = None
    source: str | None = None


@dataclass
class SequenceInfo:
    """Information about a sequence."""

    name: str
    category: str
    description: str
    source: str
    vendor: str | None = None
    commands: list[str] | None = None
    timeout: float | None = None
    device_types: list[str] | None = None


def get_device_list(config: NetworkConfig) -> list[DeviceInfo]:
    """Get list of configured devices."""
    catalog = get_inventory_catalog(config)
    if catalog is None:
        if not config.devices:
            return []

        result = []
        for name, device in config.devices.items():
            # Find groups this device belongs to
            groups = []
            if config.device_groups:
                for group_name, group in config.device_groups.items():
                    if group.members and name in group.members:
                        groups.append(group_name)

            result.append(
                DeviceInfo(
                    name=name,
                    hostname=device.host,
                    device_type=device.device_type,
                    transport=config.get_transport_type(name),
                    groups=sorted(groups),
                    description=device.description,
                    tags=device.tags,
                    source=_source_from_config(config, name, kind="device"),
                )
            )
        return sorted(result, key=lambda x: x.name)

    memberships = _group_memberships_by_source(catalog)
    devices: list[DeviceInfo] = []
    for entry in catalog.list_device_entries():
        transport = entry.device.transport_type or config.general.default_transport_type
        groups = sorted(memberships.get((entry.ref.source_id, entry.name), set()))
        devices.append(
            DeviceInfo(
                name=entry.name,
                hostname=entry.device.host,
                device_type=entry.device.device_type,
                transport=transport,
                groups=groups,
                description=entry.device.description,
                tags=entry.device.tags,
                source=_format_source(entry.ref.kind, entry.ref.source_id),
            )
        )
    return sorted(devices, key=lambda x: (x.name, x.source or ""))


def get_group_list(config: NetworkConfig) -> list[GroupInfo]:
    """Get list of configured groups."""
    catalog = get_inventory_catalog(config)
    if catalog is None:
        if not config.device_groups:
            return []

        result = []
        for name, group in config.device_groups.items():
            result.append(
                GroupInfo(
                    name=name,
                    members=sorted(group.members or []),
                    description=group.description,
                    match_tags=group.match_tags,
                    source=_source_from_config(config, name, kind="group"),
                )
            )
        return sorted(result, key=lambda x: x.name)

    groups: list[GroupInfo] = []
    for entry in catalog.list_group_entries():
        groups.append(
            GroupInfo(
                name=entry.name,
                members=sorted(entry.group.members or []),
                description=entry.group.description,
                match_tags=entry.group.match_tags,
                source=_format_source(entry.ref.kind, entry.ref.source_id),
            )
        )
    return sorted(groups, key=lambda x: (x.name, x.source or ""))


def _format_source(kind: str, source_id: str) -> str:
    if kind == "config" and source_id == "config":
        return "config"
    if kind == "discovered":
        return f"local:{source_id}"
    if kind == "cli":
        return f"cli:{source_id}"
    if kind == "config_inventory":
        return f"config:{source_id}"
    return f"{kind}:{source_id}"


def _source_from_config(config: NetworkConfig, name: str, *, kind: str) -> str:
    if kind == "device":
        getter = getattr(config, "get_device_inventory_source_id", None)
    else:
        getter = getattr(config, "get_group_inventory_source_id", None)

    if callable(getter):
        try:
            value = getter(name)
        except Exception:
            value = None
        if isinstance(value, str) and value:
            return value
    return "config"


def _group_memberships_by_source(catalog: Any) -> dict[tuple[str, str], set[str]]:
    memberships: dict[tuple[str, str], set[str]] = {}

    for group_name, entries in catalog.groups_by_name.items():
        for entry in entries:
            source_id = entry.ref.source_id
            for member in entry.group.members or []:
                memberships.setdefault((source_id, member), set()).add(group_name)

    # Tag-based membership is only supported for config source in v1.
    for group_name, entries in catalog.groups_by_name.items():
        for entry in entries:
            if entry.ref.source_id != "config":
                continue
            tags = set(entry.group.match_tags or [])
            if not tags:
                continue
            for dev_entries in catalog.devices_by_name.values():
                for dev_entry in dev_entries:
                    if dev_entry.ref.source_id != "config":
                        continue
                    dev_tags = set(dev_entry.device.tags or [])
                    if tags.issubset(dev_tags):
                        memberships.setdefault(("config", dev_entry.name), set()).add(
                            group_name
                        )
                        break

    return memberships


def get_sequence_list(
    config: NetworkConfig,
    vendor: str | None = None,
    category: str | None = None,
) -> list[SequenceInfo]:
    """Get list of available sequences."""
    sm = SequenceManager(config)
    result = []

    def _create_info(
        name: str, seq: SequenceRecord, v_name: str | None
    ) -> SequenceInfo:
        cmds = []
        if seq.commands:
            if isinstance(seq.commands[0], str):
                cmds = seq.commands
            else:
                cmds = [cmd.command for cmd in seq.commands]

        return SequenceInfo(
            name=name,
            category=seq.category,
            description=seq.description,
            source=seq.source,
            vendor=v_name,
            commands=cmds,
            timeout=seq.timeout,
            device_types=seq.device_types,
        )

    if vendor:
        vendor_seqs = sm.list_vendor_sequences(vendor)
        if not vendor_seqs:
            return []

        for name, seq in vendor_seqs.items():
            if category and seq.category != category:
                continue
            result.append(_create_info(name, seq, vendor))
    else:
        all_vendor = sm.list_all_sequences()
        for v_name, sequences in all_vendor.items():
            for name, seq in sequences.items():
                if category and seq.category != category:
                    continue
                result.append(_create_info(name, seq, v_name))

    return sorted(result, key=lambda x: (x.vendor or "", x.name))
