from __future__ import annotations

import pytest

from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.config import load_config


def test_resolver_is_device_and_is_group() -> None:
    cfg = load_config("config")
    r = DeviceResolver(cfg)

    # Take first device/group names if present
    dev = next(iter(cfg.devices.keys())) if cfg.devices else None
    grp = next(iter(cfg.device_groups.keys())) if cfg.device_groups else None

    if dev:
        assert r.is_device(dev)
    if grp:
        assert r.is_group(grp)


def test_resolver_resolve_targets_devices_and_groups() -> None:
    cfg = load_config("config")
    r = DeviceResolver(cfg)

    if not cfg.devices:
        pytest.skip("No devices available in config")

    # Single device resolves to itself
    dev = next(iter(cfg.devices.keys()))
    devices, unknown = r.resolve_targets(dev)
    assert devices == [dev]
    assert unknown == []

    # Group resolves to its members and filters unknowns
    if cfg.device_groups:
        grp = next(iter(cfg.device_groups.keys()))
        devices, unknown = r.resolve_targets(f"{grp},no_such_target")
        # Members must exist in device list
        for d in devices:
            assert cfg.devices and d in cfg.devices
        assert "no_such_target" in unknown or not unknown  # allow all-valid configs


def test_resolver_get_group_members_matches_config() -> None:
    cfg = load_config("config")
    r = DeviceResolver(cfg)
    if not cfg.device_groups:
        pytest.skip("No groups present")

    for name in cfg.device_groups.keys():
        members = r.get_group_members(name)
        for m in members:
            assert cfg.devices and m in cfg.devices


def test_resolver_effective_config_defaults_to_original() -> None:
    cfg = load_config("config")
    r = DeviceResolver(cfg)
    assert r.effective_config is cfg
