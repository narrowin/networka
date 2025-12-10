"""Programmatic API for retrieving information about devices, groups, and sequences."""

from __future__ import annotations

from dataclasses import dataclass

from network_toolkit.config import NetworkConfig
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.sequence_manager import SequenceManager


@dataclass
class InfoOptions:
    """Options for the info operation."""

    targets: str
    config: NetworkConfig
    vendor: str | None = None
    verbose: bool = False


@dataclass
class InfoTarget:
    """Resolved target information."""

    name: str
    type: str  # "device", "group", "sequence"


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

    sm = SequenceManager(options.config)
    all_sequences = sm.list_all_sequences()

    def _determine_target_type(target: str) -> str:
        # Check if it's a device
        if options.config.devices and target in options.config.devices:
            return "device"

        # Check if it's a group
        if options.config.device_groups and target in options.config.device_groups:
            return "group"

        # Check if it's a vendor sequence
        for vendor_sequences in all_sequences.values():
            if target in vendor_sequences:
                return "sequence"

        return "unknown"

    for target in target_list:
        target_type = _determine_target_type(target)

        if target_type == "unknown":
            unknown_targets.append(target)
        else:
            targets.append(InfoTarget(name=target, type=target_type))
            if target_type == "device":
                device_count += 1

    return InfoResult(
        targets=targets,
        unknown_targets=unknown_targets,
        device_count=device_count,
    )
