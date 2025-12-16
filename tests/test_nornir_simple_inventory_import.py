from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from network_toolkit.config import load_modular_config
from network_toolkit.exceptions import ConfigurationError


def _write_yaml(path: Path, content: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(content, f)


def test_nornir_simple_inventory_containerlab_single_file(tmp_path: Path) -> None:
    inventory_file = tmp_path / "nornir-simple-inventory.yml"
    _write_yaml(
        inventory_file,
        {
            "node1": {
                "hostname": "172.200.20.2",
                "platform": "nokia_srlinux",
                "username": "admin",
                "password": "pw1",
                "groups": ["spine"],
            },
            "node2": {
                "hostname": "172.200.20.3",
                "platform": "arista_eos",
                "username": "admin",
                "password": "pw2",
                "groups": ["spine", "leaf"],
            },
        },
    )

    _write_yaml(
        tmp_path / "config.yml",
        {
            "general": {"timeout": 30},
            "inventory": {
                "source": "nornir_simple",
                "nornir_inventory_dir": "nornir-simple-inventory.yml",
                "merge_mode": "replace",
                "credentials_mode": "env",
                "group_membership": "extended",
            },
        },
    )

    cfg = load_modular_config(tmp_path)
    assert cfg.devices is not None
    assert sorted(cfg.devices.keys()) == ["node1", "node2"]
    assert cfg.devices["node1"].host == "172.200.20.2"
    assert cfg.devices["node1"].device_type == "nokia_srlinux"
    assert cfg.devices["node1"].user is None
    assert cfg.devices["node1"].password is None

    assert cfg.device_groups is not None
    assert sorted(cfg.device_groups.keys()) == ["leaf", "spine"]
    assert cfg.device_groups["spine"].members == ["node1", "node2"]
    assert cfg.device_groups["leaf"].members == ["node2"]


def test_nornir_simple_inventory_containerlab_dir_detection(tmp_path: Path) -> None:
    inv_dir = tmp_path / "lab"
    inv_dir.mkdir()

    _write_yaml(
        inv_dir / "nornir-simple-inventory.yaml",
        {
            "node1": {"hostname": "10.0.0.1", "platform": "linux"},
        },
    )

    _write_yaml(
        tmp_path / "config.yml",
        {
            "general": {"timeout": 30},
            "inventory": {
                "source": "nornir_simple",
                "nornir_inventory_dir": "lab",
                "merge_mode": "replace",
            },
        },
    )

    cfg = load_modular_config(tmp_path)
    assert cfg.devices is not None
    assert "node1" in cfg.devices
    assert cfg.devices["node1"].host == "10.0.0.1"
    assert cfg.devices["node1"].device_type == "linux"


def test_nornir_simple_inventory_containerlab_connect_host_longname(
    tmp_path: Path,
) -> None:
    inv_dir = tmp_path / "clab-s3n"
    inv_dir.mkdir()

    _write_yaml(
        inv_dir / "nornir-simple-inventory.yml",
        {
            "sw-acc1": {
                "hostname": "10.10.1.11",
                "platform": "mikrotik_ros",
                "username": "admin",
                "password": "admin",
            }
        },
    )

    _write_yaml(
        tmp_path / "config.yml",
        {
            "inventory": {
                "source": "nornir_simple",
                "nornir_inventory_dir": "clab-s3n",
                "merge_mode": "replace",
                "credentials_mode": "inventory",
                "platform_mapping": "netmiko_to_networka",
                "connect_host": "containerlab_longname",
            }
        },
    )

    cfg = load_modular_config(tmp_path)
    assert cfg.devices is not None
    assert cfg.devices["sw-acc1"].host == "clab-s3n-sw-acc1"
    assert cfg.devices["sw-acc1"].device_type == "mikrotik_routeros"


def test_nornir_simple_inventory_missing_platform_is_error(tmp_path: Path) -> None:
    inventory_file = tmp_path / "hosts.yml"
    _write_yaml(
        inventory_file,
        {
            "node1": {"hostname": "10.0.0.1"},
        },
    )

    _write_yaml(
        tmp_path / "config.yml",
        {
            "general": {"timeout": 30},
            "inventory": {
                "source": "nornir_simple",
                "nornir_inventory_dir": "hosts.yml",
                "merge_mode": "replace",
            },
        },
    )

    with pytest.raises(ConfigurationError, match="Missing required 'platform'"):
        load_modular_config(tmp_path)


def test_nornir_simple_inventory_credentials_mode_inventory_sets_device_creds(
    tmp_path: Path,
) -> None:
    inventory_file = tmp_path / "hosts.yml"
    _write_yaml(
        inventory_file,
        {
            "node1": {
                "hostname": "10.0.0.1",
                "platform": "linux",
                "username": "u",
                "password": "p",
            }
        },
    )

    _write_yaml(
        tmp_path / "config.yml",
        {
            "general": {"timeout": 30},
            "inventory": {
                "source": "nornir_simple",
                "nornir_inventory_dir": "hosts.yml",
                "merge_mode": "replace",
                "credentials_mode": "inventory",
            },
        },
    )

    cfg = load_modular_config(tmp_path)
    assert cfg.devices is not None
    assert cfg.devices["node1"].user == "u"
    assert cfg.devices["node1"].password == "p"


def test_nornir_simple_inventory_ambiguous_group_env_credentials_fails(
    tmp_path: Path,
) -> None:
    inventory_file = tmp_path / "nornir-simple-inventory.yml"
    _write_yaml(
        inventory_file,
        {
            "node1": {
                "hostname": "10.0.0.1",
                "platform": "linux",
                "groups": ["spine", "leaf"],
            }
        },
    )

    _write_yaml(
        tmp_path / "config.yml",
        {
            "general": {"timeout": 30},
            "inventory": {
                "source": "nornir_simple",
                "nornir_inventory_dir": "nornir-simple-inventory.yml",
                "merge_mode": "replace",
                "credentials_mode": "env",
                "group_membership": "extended",
            },
        },
    )

    # Two group credential sources => ambiguous in v1 (env mode).
    import os

    os.environ["NW_PASSWORD_SPINE"] = "x"
    os.environ["NW_PASSWORD_LEAF"] = "y"
    try:
        with pytest.raises(
            ConfigurationError, match="Ambiguous group-level env credentials"
        ):
            load_modular_config(tmp_path)
    finally:
        os.environ.pop("NW_PASSWORD_SPINE", None)
        os.environ.pop("NW_PASSWORD_LEAF", None)
