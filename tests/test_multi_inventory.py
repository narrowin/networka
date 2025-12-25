from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from network_toolkit.api.list import get_device_list
from network_toolkit.config import load_modular_config
from network_toolkit.exceptions import ConfigurationError
from network_toolkit.inventory.resolve import resolve_named_targets
from network_toolkit.runtime import set_runtime_settings


def _write_yaml(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(content, f)


def test_local_discovery_adds_containerlab_inventory_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_yaml(tmp_path / "config.yml", {"general": {}})

    clab_dir = tmp_path / "clab-demo"
    _write_yaml(
        clab_dir / "nornir-simple-inventory.yml",
        {
            "node1": {
                "hostname": "10.0.0.1",
                "platform": "mikrotik_ros",
                "username": "u",
                "password": "p",
            }
        },
    )

    cfg = load_modular_config(tmp_path)
    assert cfg.devices is not None
    assert cfg.devices["node1"].host == "clab-demo-node1"
    assert cfg.devices["node1"].device_type == "mikrotik_routeros"
    assert cfg.devices["node1"].user == "u"

    devices = get_device_list(cfg)
    assert len(devices) == 1
    assert devices[0].source == "local:clab-demo"


def test_local_discovery_can_be_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_yaml(tmp_path / "config.yml", {"inventory": {"discover_local": False}})

    clab_dir = tmp_path / "clab-demo"
    _write_yaml(
        clab_dir / "nornir-simple-inventory.yml",
        {
            "node1": {
                "hostname": "10.0.0.1",
                "platform": "linux",
            }
        },
    )

    cfg = load_modular_config(tmp_path)
    assert not cfg.devices
    assert get_device_list(cfg) == []


def test_multiple_inventory_dirs_in_config_are_additive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_yaml(
        tmp_path / "config.yml",
        {
            "inventory": {
                "discover_local": False,
                "nornir_inventory_dirs": ["./inv1", "./inv2"],
            }
        },
    )

    _write_yaml(
        tmp_path / "inv1" / "hosts.yml",
        {"dev1": {"hostname": "10.0.0.1", "platform": "linux"}},
    )
    _write_yaml(
        tmp_path / "inv2" / "hosts.yml",
        {"dev2": {"hostname": "10.0.0.2", "platform": "linux"}},
    )

    cfg = load_modular_config(tmp_path)
    devices = get_device_list(cfg)
    assert {(d.name, d.source) for d in devices} == {
        ("dev1", "config:inv1"),
        ("dev2", "config:inv2"),
    }


def test_ambiguous_device_errors_without_prefer(tmp_path: Path) -> None:
    """Test that duplicate devices across inventory sources raise an error at config load time."""
    _write_yaml(
        tmp_path / "config.yml",
        {
            "inventory": {"discover_local": False, "nornir_inventory_dir": "./inv1"},
            "devices": {"dup": {"host": "1.1.1.1", "device_type": "linux"}},
        },
    )
    _write_yaml(
        tmp_path / "inv1" / "hosts.yml",
        {"dup": {"hostname": "2.2.2.2", "platform": "linux"}},
    )

    # Error now raised at config load time, not resolution time
    with pytest.raises(
        ConfigurationError, match="exists in multiple inventory sources"
    ):
        load_modular_config(tmp_path)


def test_inventory_prefer_selects_source_for_ambiguous_device(tmp_path: Path) -> None:
    """Test that --prefer allows loading configs with duplicate devices."""
    _write_yaml(
        tmp_path / "config.yml",
        {
            "inventory": {"discover_local": False, "nornir_inventory_dir": "./inv1"},
            "devices": {"dup": {"host": "1.1.1.1", "device_type": "linux"}},
        },
    )
    _write_yaml(
        tmp_path / "inv1" / "hosts.yml",
        {"dup": {"hostname": "2.2.2.2", "platform": "linux"}},
    )

    # With prefer set, config loading should succeed (first-wins behavior)
    set_runtime_settings(inventory_prefer="config")
    cfg = load_modular_config(tmp_path)
    resolve_named_targets(cfg, "dup", prefer="config")
    assert cfg.devices is not None
    assert cfg.devices["dup"].host == "1.1.1.1"

    # Reload with different preference to get the other device
    set_runtime_settings(inventory_prefer="config:inv1")
    cfg2 = load_modular_config(tmp_path)
    resolve_named_targets(cfg2, "dup", prefer="config:inv1")
    assert cfg2.devices["dup"].host == "2.2.2.2"
    set_runtime_settings(inventory_prefer=None)  # Reset


def test_inventory_prefer_accepts_cli_prefixed_token(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "config.yml",
        {
            "inventory": {"discover_local": False},
            "devices": {"dup": {"host": "1.1.1.1", "device_type": "linux"}},
        },
    )
    inv_dir = tmp_path / "inv1"
    _write_yaml(
        inv_dir / "hosts.yml",
        {"dup": {"hostname": "2.2.2.2", "platform": "linux"}},
    )

    # Set prefer before loading to allow duplicates
    set_runtime_settings(inventory_paths=[inv_dir], inventory_prefer="cli:inv1")
    cfg = load_modular_config(tmp_path)
    resolve_named_targets(cfg, "dup", prefer="cli:inv1")
    assert cfg.devices is not None
    assert cfg.devices["dup"].host == "2.2.2.2"
    set_runtime_settings(inventory_paths=[], inventory_prefer=None)  # Reset


def test_inventory_prefer_accepts_local_prefixed_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_yaml(
        tmp_path / "config.yml",
        {"devices": {"dup": {"host": "1.1.1.1", "device_type": "linux"}}},
    )

    clab_dir = tmp_path / "clab-demo"
    _write_yaml(
        clab_dir / "nornir-simple-inventory.yml",
        {"dup": {"hostname": "10.0.0.1", "platform": "linux"}},
    )

    # Set prefer before loading to allow duplicates
    set_runtime_settings(inventory_prefer="local:clab-demo")
    cfg = load_modular_config(tmp_path)
    resolve_named_targets(cfg, "dup", prefer="local:clab-demo")
    assert cfg.devices is not None
    assert cfg.devices["dup"].host == "clab-demo-dup"
    set_runtime_settings(inventory_prefer=None)  # Reset


def test_ambiguous_group_errors_without_prefer(tmp_path: Path) -> None:
    """Test that duplicate groups across inventory sources raise an error at config load time."""
    _write_yaml(
        tmp_path / "config.yml",
        {
            "inventory": {"discover_local": False, "nornir_inventory_dir": "./inv1"},
            "devices": {"dev0": {"host": "1.1.1.1", "device_type": "linux"}},
            "device_groups": {"g1": {"description": "cfg", "members": ["dev0"]}},
        },
    )
    _write_yaml(
        tmp_path / "inv1" / "hosts.yml",
        {"dev1": {"hostname": "2.2.2.2", "platform": "linux", "groups": ["g1"]}},
    )

    # Error now raised at config load time for duplicate groups
    with pytest.raises(
        ConfigurationError, match="exists in multiple inventory sources"
    ):
        load_modular_config(tmp_path)


def test_inventory_prefer_selects_source_for_ambiguous_group(tmp_path: Path) -> None:
    """Test that --prefer allows loading configs with duplicate groups."""
    _write_yaml(
        tmp_path / "config.yml",
        {
            "inventory": {"discover_local": False, "nornir_inventory_dir": "./inv1"},
            "devices": {"dev0": {"host": "1.1.1.1", "device_type": "linux"}},
            "device_groups": {"g1": {"description": "cfg", "members": ["dev0"]}},
        },
    )
    _write_yaml(
        tmp_path / "inv1" / "hosts.yml",
        {"dev1": {"hostname": "2.2.2.2", "platform": "linux", "groups": ["g1"]}},
    )

    # With prefer set, config loading should succeed
    set_runtime_settings(inventory_prefer="config")
    cfg = load_modular_config(tmp_path)
    cfg_members = resolve_named_targets(cfg, "g1", prefer="config").resolved_devices
    assert cfg_members == ["dev0"]

    # Reload with different preference to get the other group
    set_runtime_settings(inventory_prefer="config:inv1")
    cfg2 = load_modular_config(tmp_path)
    inv_members = resolve_named_targets(
        cfg2, "g1", prefer="config:inv1"
    ).resolved_devices
    assert inv_members == ["dev1"]
    set_runtime_settings(inventory_prefer=None)  # Reset
