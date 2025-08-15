from __future__ import annotations

from typing import Any

import pytest

from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.sequence_manager import SequenceManager
from network_toolkit.tui.data import TuiData


def _non_empty_dict(d: dict[str, Any] | None) -> dict[str, Any]:
    return d or {}


def test_tui_targets_match_config_devices_and_groups() -> None:
    # Load via same discovery as CLI and TUI default
    cfg: NetworkConfig = load_config("config")
    data = TuiData("config")

    targets = data.targets()

    # Device names must match config keys (order not required)
    cfg_devices = set(_non_empty_dict(cfg.devices).keys())
    tui_devices = set(targets.devices)
    assert tui_devices == cfg_devices

    # Group names must match config keys
    cfg_groups = set(_non_empty_dict(cfg.device_groups).keys())
    tui_groups = set(targets.groups)
    assert tui_groups == cfg_groups


def test_tui_sequences_are_union_of_known_sources() -> None:
    cfg: NetworkConfig = load_config("config")
    sm = SequenceManager(cfg)
    data = TuiData("config")

    tui_seq = set(data.actions().sequences)

    # Build expected union: global + all vendor + device-defined
    expected: set[str] = set()
    if cfg.global_command_sequences:
        expected |= set(cfg.global_command_sequences.keys())

    for vendor_map in sm.list_all_sequences().values():
        expected |= set(vendor_map.keys())

    if cfg.devices:
        for dev in cfg.devices.values():
            if dev.command_sequences:
                expected |= set(dev.command_sequences.keys())

    # TUI should at least include the full union
    assert expected <= tui_seq
    # And TUI shouldn't contain obviously bogus empty names
    assert "" not in tui_seq


def test_all_groups_resolve_to_devices() -> None:
    cfg: NetworkConfig = load_config("config")

    if not cfg.device_groups:
        pytest.skip("No groups defined in config")

    found_non_empty = False
    for gname in cfg.device_groups.keys():
        members = cfg.get_group_members(gname)
        # All resolved members must be valid device names
        for m in members:
            assert cfg.devices and m in cfg.devices
        if members:
            found_non_empty = True

    # At least one group should have members (catches empty discovery regressions)
    assert found_non_empty


def test_can_resolve_a_vendor_sequence_for_a_real_device() -> None:
    cfg: NetworkConfig = load_config("config")
    sm = SequenceManager(cfg)

    assert cfg.devices, "Expected devices in config"
    # Pick the first device and get its vendor
    device_name, device = next(iter(cfg.devices.items()))
    vendor = device.device_type

    # Get vendor sequences and pick one
    vendor_seqs = sm.list_vendor_sequences(vendor)
    assert vendor_seqs, f"Expected vendor sequences for {vendor}"

    name, _ = next(iter(vendor_seqs.items()))
    resolved = sm.resolve(name, device_name)
    assert resolved and all(isinstance(c, str) and c for c in resolved)
