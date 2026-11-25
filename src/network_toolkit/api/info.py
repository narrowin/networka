"""Programmatic API for retrieving information about devices, groups, and sequences."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from network_toolkit.config import NetworkConfig
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import select_named_target
from network_toolkit.sequence_manager import SequenceManager, SequenceRecord


@dataclass
class InfoOptions:
    """Options for the info operation."""

    targets: str
    config: NetworkConfig
    vendor: str | None = None
    verbose: bool = False
    device: str | None = None


@dataclass
class InfoTarget:
    """Resolved target information."""

    name: str
    type: str  # "device", "group", "sequence"
    sequence_records: list[SequenceRecord] = field(default_factory=list)


@dataclass
class InfoResult:
    """Result of the info operation."""

    targets: list[InfoTarget]
    unknown_targets: list[str]
    device_count: int


def get_info(options: InfoOptions) -> InfoResult:
    """Retrieve information about the specified targets."""
    target_list = [t.strip() for t in options.targets.split(",") if t.strip()]
    if not target_list:
        msg = "No targets specified"
        raise NetworkToolkitError(msg)

    targets: list[InfoTarget] = []
    unknown_targets: list[str] = []
    device_count = 0

    manager = SequenceManager(options.config)
    known_sequences = manager.known_names()
    if options.device and options.vendor:
        msg = "Choose either --device or --vendor when inspecting a sequence."
        raise NetworkToolkitError(msg)

    records: Iterable[SequenceRecord]
    if options.device:
        if select_named_target(options.config, options.device) != "device":
            msg = f"Device '{options.device}' not found in configuration."
            raise NetworkToolkitError(msg)
        records = manager.list_device_sequences(options.device).values()
    elif options.vendor:
        records = manager.list_platform_sequences(options.vendor).values()
    else:
        records = manager.catalog_records()

    sequences: dict[str, list[SequenceRecord]] = {}
    for record in records:
        sequences.setdefault(record.name, []).append(record)

    for target in target_list:
        target_type = (
            None
            if target in known_sequences and (options.device or options.vendor)
            else select_named_target(options.config, target)
        )
        if target_type:
            targets.append(InfoTarget(target, target_type))
            device_count += target_type == "device"
        elif target in known_sequences:
            targets.append(InfoTarget(target, "sequence", sequences.get(target, [])))
        else:
            unknown_targets.append(target)

    return InfoResult(
        targets=targets,
        unknown_targets=unknown_targets,
        device_count=device_count,
    )
