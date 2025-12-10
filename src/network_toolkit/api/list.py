"""Programmatic API for list operations."""

from __future__ import annotations

from dataclasses import dataclass

from network_toolkit.config import NetworkConfig
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


@dataclass
class GroupInfo:
    """Information about a group."""

    name: str
    members: list[str]
    description: str | None = None
    match_tags: list[str] | None = None


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
            )
        )
    return sorted(result, key=lambda x: x.name)


def get_group_list(config: NetworkConfig) -> list[GroupInfo]:
    """Get list of configured groups."""
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
            )
        )
    return sorted(result, key=lambda x: x.name)


def get_sequence_list(
    config: NetworkConfig,
    vendor: str | None = None,
    category: str | None = None,
) -> list[SequenceInfo]:
    """Get list of available sequences."""
    sm = SequenceManager(config)
    result = []

    def _create_info(name: str, seq: SequenceRecord, v_name: str | None) -> SequenceInfo:
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
