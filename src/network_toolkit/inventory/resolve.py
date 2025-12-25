# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Target resolution across multiple inventory sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.catalog import (
    DeviceEntry,
    GroupEntry,
    InventoryCatalog,
    get_inventory_catalog,
)
from network_toolkit.runtime import get_runtime_settings

if TYPE_CHECKING:
    from network_toolkit.config import DeviceGroup, NetworkConfig


@dataclass(slots=True)
class TargetResolutionResult:
    """Result of target resolution.

    Attributes:
        resolved_devices: List of device names that were successfully resolved.
        unknown_targets: List of target names that could not be resolved.
        config: The config object with resolved devices/groups populated.
            This is the same object that was passed in (mutated in place for
            efficiency). Callers should use this reference to access the
            resolved device definitions.
    """

    resolved_devices: list[str]
    unknown_targets: list[str]
    config: NetworkConfig | None = None


def select_named_target(
    config: NetworkConfig, name: str, *, prefer: str | None = None
) -> str | None:
    """Select a device or group target by name without expanding groups.

    Returns:
        "device" | "group" | None

    Raises:
        NetworkToolkitError on ambiguity.
    """
    prefer_token = _prefer_token(prefer)
    catalog = get_inventory_catalog(config)
    if catalog is None:
        if config.devices and name in config.devices:
            return "device"
        if config.device_groups and name in config.device_groups:
            return "group"
        return None

    dev_entry = catalog.resolve_device(name, prefer=prefer_token)
    if dev_entry is not None:
        _apply_device_selection(config, name, dev_entry)
        return "device"

    grp_entry = catalog.resolve_group(name, prefer=prefer_token)
    if grp_entry is not None:
        _apply_group_selection(config, name, grp_entry)
        return "group"

    return None


def resolve_named_targets(
    config: NetworkConfig, target_expr: str, *, prefer: str | None = None
) -> TargetResolutionResult:
    """Resolve a comma-separated target expression to concrete device names.

    This resolver:
    - Detects ambiguity across inventory sources and raises an error unless a
      preference is provided.
    - Expands groups into their member devices, selecting devices from the same
      inventory source as the group definition.
    - Populates selected devices/groups into config.devices/config.device_groups
      with the chosen definitions.

    Returns:
        TargetResolutionResult with resolved_devices, unknown_targets, and the
        config object with resolved entries populated.
    """
    prefer_token = _prefer_token(prefer)
    requested = [t.strip() for t in target_expr.split(",") if t.strip()]
    if not requested:
        return TargetResolutionResult(
            resolved_devices=[], unknown_targets=[], config=config
        )

    catalog = get_inventory_catalog(config)
    if catalog is None:
        return _resolve_simple(config, requested)

    resolved: list[str] = []
    unknown: list[str] = []

    def _add_device(name: str) -> None:
        if name not in resolved:
            resolved.append(name)

    for name in requested:
        dev_entry = catalog.resolve_device(name, prefer=prefer_token)
        if dev_entry is not None:
            _apply_device_selection(config, name, dev_entry)
            _add_device(name)
            continue

        grp_entry = catalog.resolve_group(name, prefer=prefer_token)
        if grp_entry is None:
            unknown.append(name)
            continue

        _apply_group_selection(config, name, grp_entry)
        members = _group_members_in_source(config, grp_entry, catalog)
        for member_name, member_entry in members:
            _apply_device_selection(config, member_name, member_entry)
            _add_device(member_name)

    return TargetResolutionResult(
        resolved_devices=resolved, unknown_targets=unknown, config=config
    )


def list_unique_device_names(config: NetworkConfig) -> list[str]:
    catalog = get_inventory_catalog(config)
    if catalog is None:
        return sorted(config.devices.keys()) if config.devices else []
    return sorted(catalog.devices_by_name.keys())


def list_unique_group_names(config: NetworkConfig) -> list[str]:
    catalog = get_inventory_catalog(config)
    if catalog is None:
        return sorted(config.device_groups.keys()) if config.device_groups else []
    return sorted(catalog.groups_by_name.keys())


def _resolve_simple(
    config: NetworkConfig, requested: list[str]
) -> TargetResolutionResult:
    devices: list[str] = []
    unknowns: list[str] = []

    def _add_device(name: str) -> None:
        if name not in devices:
            devices.append(name)

    for name in requested:
        if config.devices and name in config.devices:
            _add_device(name)
            continue
        if config.device_groups and name in config.device_groups:
            group = config.device_groups[name]
            members: list[str]
            match_tags: list[str]

            # Support legacy group formats used in tests/older configs.
            if isinstance(group, list | tuple | set):
                members = [str(m) for m in group]
                match_tags = []
            elif isinstance(group, dict):
                members = [str(m) for m in (group.get("members") or [])]
                match_tags = [str(t) for t in (group.get("match_tags") or [])]
            else:
                members = [str(m) for m in (getattr(group, "members", None) or [])]
                match_tags = [
                    str(t) for t in (getattr(group, "match_tags", None) or [])
                ]

            for member in members:
                _add_device(member)

            if match_tags and config.devices:
                tags = set(match_tags)
                for dev_name, dev in config.devices.items():
                    dev_tags = set(getattr(dev, "tags", None) or [])
                    if tags.issubset(dev_tags):
                        _add_device(dev_name)
            continue
        unknowns.append(name)

    return TargetResolutionResult(
        resolved_devices=devices, unknown_targets=unknowns, config=config
    )


def _apply_device_selection(
    config: NetworkConfig, name: str, entry: DeviceEntry
) -> None:
    if config.devices is None:
        config.devices = {}
    config.devices[name] = entry.device


def _apply_group_selection(config: NetworkConfig, name: str, entry: GroupEntry) -> None:
    if config.device_groups is None:
        config.device_groups = {}
    config.device_groups[name] = entry.group


def _group_members_in_source(
    config: NetworkConfig, group_entry: GroupEntry, catalog: InventoryCatalog
) -> list[tuple[str, DeviceEntry]]:
    source_id = group_entry.ref.source_id
    group: DeviceGroup = group_entry.group
    members = list(group.members or [])

    # Tag-based membership is only supported for config source in v1.
    if source_id == "config" and group.match_tags:
        tags = set(group.match_tags)
        for dev_name, entries in catalog.devices_by_name.items():
            for entry in entries:
                if entry.ref.source_id != "config":
                    continue
                dev_tags = set(getattr(entry.device, "tags", None) or [])
                if tags.issubset(dev_tags):
                    if dev_name not in members:
                        members.append(dev_name)
                    break

    resolved: list[tuple[str, DeviceEntry]] = []
    for member in members:
        entry = catalog.resolve_device(member, source_id=source_id)
        if entry is None:
            msg = f"Group '{group_entry.name}' references unknown device '{member}'"
            raise NetworkToolkitError(
                msg,
                details={
                    "group": group_entry.name,
                    "device": member,
                    "source_id": source_id,
                },
            )
        resolved.append((member, entry))
    return resolved


def _prefer_token(prefer: str | None) -> str | None:
    if prefer is not None:
        return prefer
    return get_runtime_settings().inventory_prefer
