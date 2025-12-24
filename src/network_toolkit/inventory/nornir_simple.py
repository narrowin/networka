"""Import Nornir SimpleInventory (and containerlab output) into Networka config models.

This module intentionally focuses on inventory ingestion only. Networka execution logic
continues to operate on `NetworkConfig.devices` and `NetworkConfig.device_groups`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from network_toolkit.exceptions import ConfigurationError

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class CompiledInventory:
    devices: dict[str, dict[str, Any]]
    device_groups: dict[str, dict[str, Any]]
    device_sources: dict[str, Path]
    group_sources: dict[str, Path]


def compile_nornir_simple_inventory(
    *,
    config_dir: Path,
    inventory_path: Path,
    credentials_mode: str = "env",
    group_membership: str = "extended",
    platform_mapping: str = "none",
    connect_host: str = "inventory_hostname",
) -> CompiledInventory:
    """Compile a Nornir SimpleInventory into Networka devices and groups.

    Supported input layouts:
    - Standard directory: hosts.(yml|yaml) plus optional groups/defaults
    - Containerlab directory: nornir-simple-inventory.(yml|yaml)
    - Single file: a hosts-style YAML mapping (containerlab output)
    """
    if credentials_mode not in {"env", "inventory"}:
        msg = "Invalid inventory.credentials_mode; expected 'env' or 'inventory'"
        raise ConfigurationError(msg, details={"credentials_mode": credentials_mode})
    if group_membership not in {"extended", "direct"}:
        msg = "Invalid inventory.group_membership; expected 'extended' or 'direct'"
        raise ConfigurationError(msg, details={"group_membership": group_membership})
    if platform_mapping not in {"none", "netmiko_to_networka"}:
        msg = "Invalid inventory.platform_mapping; expected 'none' or 'netmiko_to_networka'"
        raise ConfigurationError(msg, details={"platform_mapping": platform_mapping})
    if connect_host not in {"inventory_hostname", "host_key", "containerlab_longname"}:
        msg = (
            "Invalid inventory.connect_host; expected 'inventory_hostname', 'host_key', "
            "or 'containerlab_longname'"
        )
        raise ConfigurationError(msg, details={"connect_host": connect_host})

    resolved_path = inventory_path
    if not resolved_path.is_absolute():
        resolved_path = config_dir / resolved_path
    resolved_path = resolved_path.resolve()

    host_file, groups_file, defaults_file = _detect_inventory_files(resolved_path)
    containerlab_prefix = _maybe_containerlab_prefix(resolved_path, host_file)
    hosts_raw = _load_yaml_mapping(host_file, "hosts inventory")
    groups_raw = (
        _load_yaml_mapping(groups_file, "groups inventory") if groups_file else {}
    )
    defaults_raw = (
        _load_yaml_mapping(defaults_file, "defaults inventory") if defaults_file else {}
    )

    _validate_names(hosts_raw.keys(), what="host")
    _validate_names(groups_raw.keys(), what="group")

    resolved_groups = _resolve_group_effective_vars(groups_raw)

    devices: dict[str, dict[str, Any]] = {}
    device_sources: dict[str, Path] = {}

    # For group membership we want deterministic ordering of keys for downstream behavior.
    group_members: dict[str, set[str]] = {}

    for host_name, host_cfg in hosts_raw.items():
        if not isinstance(host_cfg, dict):
            msg = "Invalid host entry in Nornir inventory; expected mapping"
            raise ConfigurationError(
                msg,
                details={"host": host_name, "type": type(host_cfg).__name__},
            )

        effective = _resolve_host_effective_vars(
            host_cfg=host_cfg,
            defaults=defaults_raw,
            group_effective=resolved_groups,
        )

        hostname = effective.get("hostname")
        platform = effective.get("platform")
        port = effective.get("port")
        username = effective.get("username")
        password = effective.get("password")

        if not hostname or not isinstance(hostname, str):
            msg = "Missing required 'hostname' for host in Nornir inventory"
            raise ConfigurationError(
                msg, details={"host": host_name, "inventory_file": str(host_file)}
            )
        if not platform or not isinstance(platform, str):
            msg = "Missing required 'platform' for host in Nornir inventory"
            raise ConfigurationError(
                msg, details={"host": host_name, "inventory_file": str(host_file)}
            )

        mapped_platform = (
            _map_platform(platform)
            if platform_mapping == "netmiko_to_networka"
            else platform
        )

        device_host = _select_device_host(
            connect_host=connect_host,
            host_key=host_name,
            inventory_hostname=hostname,
            containerlab_prefix=containerlab_prefix,
        )

        device: dict[str, Any] = {
            "host": device_host,
            "device_type": mapped_platform,
        }

        if isinstance(port, int):
            device["port"] = port
        elif isinstance(port, str) and port.isdigit():
            device["port"] = int(port)

        if credentials_mode == "inventory":
            if isinstance(username, str) and username:
                device["user"] = username
            if isinstance(password, str) and password:
                device["password"] = password

        devices[host_name] = device
        device_sources[host_name] = host_file

        direct_groups = host_cfg.get("groups") or []
        if direct_groups is None:
            direct_groups = []
        if not isinstance(direct_groups, list) or not all(
            isinstance(g, str) for g in direct_groups
        ):
            msg = "Invalid 'groups' for host in Nornir inventory; expected list[str]"
            raise ConfigurationError(
                msg, details={"host": host_name, "inventory_file": str(host_file)}
            )

        _validate_names(direct_groups, what="group")

        if group_membership == "direct":
            membership_groups = set(direct_groups)
        else:
            membership_groups = set()
            for g in direct_groups:
                membership_groups.update(_group_closure(g, groups_raw))

        for group_name in membership_groups:
            group_members.setdefault(group_name, set()).add(host_name)

    device_groups: dict[str, dict[str, Any]] = {}
    group_sources: dict[str, Path] = {}

    # Always create a group entry for every group seen in membership, even if no groups.yaml exists.
    for group_name in sorted(group_members.keys()):
        members_sorted = sorted(group_members[group_name])
        device_groups[group_name] = {
            "description": "Imported from Nornir",
            "members": members_sorted,
            # Ensure Networka will evaluate group env vars (see NetworkConfig.get_group_credentials).
            "credentials": {},
        }
        group_sources[group_name] = host_file

    if credentials_mode == "env":
        _fail_on_ambiguous_group_env_credentials(
            devices=devices,
            groups_for_device={
                h: _device_groups_for_host(h, hosts_raw, groups_raw, group_membership)
                for h in devices
            },
        )

    return CompiledInventory(
        devices=devices,
        device_groups=device_groups,
        device_sources=device_sources,
        group_sources=group_sources,
    )


def _detect_inventory_files(path: Path) -> tuple[Path, Path | None, Path | None]:
    if path.is_file():
        if path.suffix.lower() not in {".yml", ".yaml"}:
            msg = "Unsupported inventory file type; expected .yml or .yaml"
            raise ConfigurationError(msg, details={"path": str(path)})
        return path, None, None

    if not path.exists() or not path.is_dir():
        msg = "Inventory path does not exist or is not a directory"
        raise ConfigurationError(msg, details={"path": str(path)})

    containerlab_candidates = [
        path / "nornir-simple-inventory.yml",
        path / "nornir-simple-inventory.yaml",
    ]
    for candidate in containerlab_candidates:
        if candidate.exists():
            return candidate, None, None

    host_file = _first_existing(path, ["hosts.yml", "hosts.yaml"])
    if host_file is None:
        msg = "Nornir inventory directory missing hosts file"
        raise ConfigurationError(
            msg,
            details={
                "path": str(path),
                "expected": ["hosts.yml", "hosts.yaml", "nornir-simple-inventory.yml"],
            },
        )

    groups_file = _first_existing(path, ["groups.yml", "groups.yaml"])
    defaults_file = _first_existing(path, ["defaults.yml", "defaults.yaml"])
    return host_file, groups_file, defaults_file


def _maybe_containerlab_prefix(inventory_path: Path, host_file: Path) -> str | None:
    """Best-effort containerlab labdir prefix.

    Containerlab typically writes artifacts into a lab directory named `clab-<labname>`,
    and nodes are addressable as `clab-<labname>-<node>`.
    """
    candidates: list[Path] = []
    if inventory_path.is_dir():
        candidates.append(inventory_path)
    candidates.append(host_file.parent)

    for cand in candidates:
        name = cand.name
        if name.startswith("clab-") and len(name) > len("clab-"):
            return name
    return None


def _select_device_host(
    *,
    connect_host: str,
    host_key: str,
    inventory_hostname: str,
    containerlab_prefix: str | None,
) -> str:
    if connect_host == "inventory_hostname":
        return inventory_hostname
    if connect_host == "host_key":
        return host_key
    # containerlab_longname
    if not containerlab_prefix:
        msg = (
            "inventory.connect_host=containerlab_longname requires inventory path to be within "
            "a containerlab lab directory (clab-<name>)"
        )
        raise ConfigurationError(
            msg,
            details={
                "connect_host": connect_host,
                "host_key": host_key,
                "inventory_hostname": inventory_hostname,
            },
        )
    return f"{containerlab_prefix}-{host_key}"


def _first_existing(base: Path, names: list[str]) -> Path | None:
    for name in names:
        p = base / name
        if p.exists():
            return p
    return None


def _load_yaml_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        msg = f"Invalid YAML in {label}"
        details: dict[str, Any] = {"path": str(path)}
        # Preserve line number information from YAML parser
        if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            mark = exc.problem_mark
            details["line"] = mark.line + 1  # 0-indexed to 1-indexed
            details["column"] = mark.column + 1
            msg = f"{msg} at line {mark.line + 1}, column {mark.column + 1}"
        if hasattr(exc, "problem") and exc.problem:
            details["problem"] = exc.problem
        raise ConfigurationError(msg, details=details) from exc
    except OSError as exc:  # pragma: no cover
        msg = f"Failed reading {label}"
        raise ConfigurationError(
            msg, details={"path": str(path), "error": str(exc)}
        ) from exc

    if not isinstance(data, dict):
        msg = f"Invalid {label}; expected YAML mapping at top-level"
        raise ConfigurationError(
            msg, details={"path": str(path), "type": type(data).__name__}
        )
    return dict(data)


def _validate_names(names: Any, *, what: str) -> None:
    bad: list[str] = []
    for name in names:
        if not isinstance(name, str) or not _SAFE_NAME_RE.match(name):
            bad.append(str(name))
    if bad:
        msg = (
            f"Invalid {what} name(s) in Nornir inventory; only [A-Za-z0-9_-] supported"
        )
        raise ConfigurationError(msg, details={"invalid_names": bad, "what": what})


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def _resolve_group_effective_vars(
    groups_raw: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    visiting: set[str] = set()

    def resolve(name: str) -> dict[str, Any]:
        if name in cache:
            return cache[name]
        if name in visiting:
            msg = "Cycle detected in Nornir groups inheritance"
            raise ConfigurationError(msg, details={"group": name})
        visiting.add(name)

        group_cfg = groups_raw.get(name, {})
        if not isinstance(group_cfg, dict):
            msg = "Invalid group entry in Nornir inventory; expected mapping"
            raise ConfigurationError(
                msg, details={"group": name, "type": type(group_cfg).__name__}
            )

        effective: dict[str, Any] = {}
        parents = group_cfg.get("groups") or []
        if parents is None:
            parents = []
        if not isinstance(parents, list) or not all(
            isinstance(p, str) for p in parents
        ):
            msg = "Invalid group 'groups' inheritance list; expected list[str]"
            raise ConfigurationError(msg, details={"group": name})
        _validate_names(parents, what="group")

        for parent in parents:
            effective = _deep_merge(effective, resolve(parent))

        own = {k: v for k, v in group_cfg.items() if k != "groups"}
        effective = _deep_merge(effective, own)
        cache[name] = effective
        visiting.remove(name)
        return effective

    for group_name in groups_raw.keys():
        resolve(group_name)
    return cache


def _resolve_host_effective_vars(
    *,
    host_cfg: dict[str, Any],
    defaults: dict[str, Any],
    group_effective: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    effective = dict(defaults)

    host_groups = host_cfg.get("groups") or []
    if host_groups is None:
        host_groups = []
    if not isinstance(host_groups, list) or not all(
        isinstance(g, str) for g in host_groups
    ):
        msg = "Invalid host 'groups' list; expected list[str]"
        raise ConfigurationError(msg, details={"groups": host_groups})

    for group_name in host_groups:
        effective = _deep_merge(effective, group_effective.get(group_name, {}))

    own = {k: v for k, v in host_cfg.items() if k != "groups"}
    effective = _deep_merge(effective, own)
    return effective


def _group_closure(group_name: str, groups_raw: dict[str, Any]) -> set[str]:
    seen: set[str] = set()
    stack = [group_name]
    while stack:
        g = stack.pop()
        if g in seen:
            continue
        seen.add(g)
        cfg = groups_raw.get(g)
        if isinstance(cfg, dict):
            parents = cfg.get("groups") or []
            if isinstance(parents, list):
                for p in parents:
                    if isinstance(p, str):
                        stack.append(p)
    return seen


def _device_groups_for_host(
    host_name: str,
    hosts_raw: dict[str, Any],
    groups_raw: dict[str, Any],
    group_membership: str,
) -> set[str]:
    cfg = hosts_raw.get(host_name, {}) or {}
    if not isinstance(cfg, dict):
        return set()
    direct = cfg.get("groups") or []
    if not isinstance(direct, list):
        return set()
    direct_groups = [g for g in direct if isinstance(g, str)]
    if group_membership == "direct":
        return set(direct_groups)
    closure: set[str] = set()
    for g in direct_groups:
        closure.update(_group_closure(g, groups_raw))
    return closure


def _fail_on_ambiguous_group_env_credentials(
    *,
    devices: dict[str, dict[str, Any]],
    groups_for_device: dict[str, set[str]],
) -> None:
    def env_var_name(group: str, kind: str) -> str:
        # Keep consistent with EnvironmentCredentialManager.get_group_specific.
        return f"NW_{kind}_{group.upper().replace('-', '_')}"

    for device_name in devices.keys():
        groups = groups_for_device.get(device_name, set())
        groups_with_creds: list[dict[str, Any]] = []
        for group in sorted(groups):
            u = os.getenv(env_var_name(group, "USER"))
            p = os.getenv(env_var_name(group, "PASSWORD"))
            if u or p:
                groups_with_creds.append(
                    {
                        "group": group,
                        "env_user": env_var_name(group, "USER") if u else None,
                        "env_password": env_var_name(group, "PASSWORD") if p else None,
                    }
                )
        if len(groups_with_creds) > 1:
            msg = (
                "Ambiguous group-level env credentials for device (multiple matching groups). "
                "Set device-specific env vars, consolidate to one group, or use inventory credentials."
            )
            raise ConfigurationError(
                msg,
                details={
                    "device": device_name,
                    "groups_with_credentials": groups_with_creds,
                    "remediation": {
                        "device_env_vars": [
                            f"NW_USER_{device_name.upper().replace('-', '_')}",
                            f"NW_PASSWORD_{device_name.upper().replace('-', '_')}",
                        ],
                        "credentials_mode": "inventory",
                    },
                },
            )


def _map_platform(platform: str) -> str:
    # Minimal pragmatic mappings. This can be extended as real-world needs appear.
    mapping = {
        # Common Netmiko-ish/other naming to Networka device_type keys
        "cisco_xe": "cisco_iosxe",
        "cisco_xr": "cisco_iosxr",
        # Containerlab often uses Netmiko-ish schema names; map to Networka keys
        "mikrotik_ros": "mikrotik_routeros",
        "nokia_srl": "nokia_srlinux",
    }
    return mapping.get(platform, platform)
