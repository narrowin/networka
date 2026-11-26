# SPDX-License-Identifier: MIT
"""Device-state intent: neutral checks, intent files, run and replay.

A platform module collects replies through `NetworkaClient.run` and keeps
each one as a `Reply`. Its normalizers turn that evidence into neutral fields,
or raise `ValueError` when the evidence cannot decide. The checks here compare
those fields with the expectation and never see command text, so saved
evidence replays to the same verdict without the device.

Every check and every intent run ends in `pass`, `fail` or `error`. `error`
means the state could not be verified and is never a pass.
"""

from __future__ import annotations

import importlib
import ipaddress
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict

import yaml

from network_toolkit.__about__ import __version__
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import select_named_target

if TYPE_CHECKING:
    from collections.abc import Collection
    from types import ModuleType

    from network_toolkit.client import NetworkaClient

Verdict = Literal["pass", "fail", "error"]

PLATFORMS = {
    "mikrotik_routeros": "network_toolkit.platforms.mikrotik_routeros.intent",
    "linux": "network_toolkit.platforms.linux.intent",
}

# Field names of the normalized state each check compares.
BRIDGE_PORT = ("forwarding", "role", "edge")
STP_BRIDGE = (
    "bridge_id",
    "root_bridge_id",
    "root_bridge",
    "root_port",
    "topology_changes",
)
MLAG = ("connected", "role", "state")
LACP_FLAGS = (
    "activity",
    "timeout",
    "aggregation",
    "synchronization",
    "collecting",
    "distributing",
    "defaulted",
    "expired",
)
LACP_SYSTEM = ("priority", "mac")
PING = ("sent", "received", "reachable")


class Reply(TypedDict):
    """One command with its device output or error, as saved for replay."""

    command: str
    output: str | None
    error: str | None


@dataclass(frozen=True, slots=True)
class IntentResult:
    """Expected and observed value with the verdict.

    `error` means the evidence cannot decide the check. `reason` says why.
    """

    expected: Any
    observed: Any
    verdict: Verdict
    reason: str | None = None


class IntentError(NetworkToolkitError):
    """An intent file, its evidence, or an item cannot be used."""


def platform(device_type: str) -> ModuleType:
    """Return the collectors and normalizers for a Networka device type."""
    if device_type not in PLATFORMS:
        supported = ", ".join(sorted(PLATFORMS))
        msg = f"no intent checks for platform {device_type!r}; supported: {supported}"
        raise IntentError(msg)
    return importlib.import_module(PLATFORMS[device_type])


def read(
    client: NetworkaClient, device: str, command: str, run_options: Mapping[str, Any]
) -> Reply:
    """Run one command and keep its output or error instead of raising."""
    try:
        result = client.run(device, command, **run_options)
    except NetworkToolkitError as error:
        return {"command": command, "output": None, "error": error.message}
    rows = [row for row in result.command_results if row.device == device]
    if len(rows) != 1:
        msg = f"expected one command result for {device}, got {len(rows)}"
        return {"command": command, "output": None, "error": msg}
    return {"command": command, "output": rows[0].output, "error": rows[0].error}


def reply_output(
    evidence: Mapping[str, Any], key: str, command: str | None = None
) -> str:
    """The output of the reply saved under `key`, which must be for `command`.

    `command` defaults to `key`, as collectors key replies by their command.
    """
    reply = evidence.get(key)
    if not isinstance(reply, dict):
        msg = f"no {key} reply in the evidence"
        raise ValueError(msg)
    if "error" not in reply or reply["error"] is not None:
        # Only `error: null` marks a successful read.
        error = reply.get("error", "no error field")
        if not isinstance(error, str) or not error:
            error = f"{key} reply error: {error!r}"
        raise ValueError(error)
    if reply.get("command") != (key if command is None else command):
        msg = f"{key} reply is for a different command"
        raise ValueError(msg)
    output = reply.get("output")
    if not isinstance(output, str):
        msg = f"{key} reply has no output"
        raise ValueError(msg)
    return output


def same(expected: Any, observed: Any) -> bool:
    """Equality that also requires the same type, recursively.

    `True` is not `1` and `110` is not `110.0`.
    """
    if type(expected) is not type(observed):
        return False
    if isinstance(expected, dict):
        keys = {(type(key), key) for key in expected}
        return keys == {(type(key), key) for key in observed} and all(
            same(value, observed[key]) for key, value in expected.items()
        )
    if isinstance(expected, list | tuple):
        return len(expected) == len(observed) and all(
            same(a, b) for a, b in zip(expected, observed, strict=True)
        )
    return bool(expected == observed)


def _unique(pairs: list[tuple[Any, Any]]) -> dict[Any, Any]:
    keys = [key for key, _ in pairs]
    if duplicates := sorted({repr(key) for key in keys if keys.count(key) > 1}):
        msg = f"duplicate keys {', '.join(duplicates)}"
        raise ValueError(msg)
    return dict(pairs)


def _no_constant(name: str) -> Any:
    msg = f"{name} is not a JSON number"
    raise ValueError(msg)


def load_json(text: str) -> Any:
    """`json.loads` that rejects duplicate keys and NaN or Infinity."""
    return json.loads(text, object_pairs_hook=_unique, parse_constant=_no_constant)


class _UniqueKeyLoader(yaml.SafeLoader):
    """A safe YAML loader that rejects duplicate mapping keys."""

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[Any, Any]:  # noqa: FBT001, FBT002 - PyYAML signature
        seen: list[Any] = []
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                msg = f"duplicate key {key!r}"
                raise yaml.constructor.ConstructorError(
                    None, None, msg, key_node.start_mark
                )
            seen.append(key)
        return super().construct_mapping(node, deep=deep)


def compare(expected: Any, observe: Callable[[], Any]) -> IntentResult:
    """`pass` when the observed value equals `expected` in value and type.

    A `ValueError` from `observe`, for evidence that cannot decide, is `error`.
    """
    try:
        observed = observe()
    except ValueError as error:
        return IntentResult(expected, None, "error", str(error))
    verdict: Verdict = "pass" if same(expected, observed) else "fail"
    return IntentResult(expected, observed, verdict)


# Names and values that reach device commands.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,63}")
MAC = re.compile(r"[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}")
MENU = re.compile(r"(/[a-z0-9-]+)+")
PROPERTY = re.compile(r"\.?[a-z][a-z0-9-]*")


def name(value: Any, what: str = "name") -> str:
    """`value` if it is a plain device object name such as `bridge` or `ether4`."""
    if not isinstance(value, str) or not NAME.fullmatch(value):
        msg = f"{what} must be a name of letters, digits, '_', '.', '/' or '-', not {value!r}"
        raise ValueError(msg)
    return value


def address(value: Any) -> str:
    """`value` if it is an IPv4 or IPv6 address, as written."""
    try:
        ipaddress.ip_address(value if isinstance(value, str) else "")
    except ValueError:
        msg = f"dest must be an IP address, not {value!r}"
        raise ValueError(msg) from None
    return str(value)


def probes(value: Any) -> int:
    """`value` if it is a whole number of ping probes from 1 to 100."""
    if type(value) is not int or not 1 <= value <= 100:
        msg = f"count must be a whole number from 1 to 100, not {value!r}"
        raise ValueError(msg)
    return int(value)


def mac(value: Any) -> str:
    """`value` if it is a MAC address written as six colon-separated byte pairs."""
    if isinstance(value, int) and not isinstance(value, bool):
        msg = f"mac {value!r} was read as a number; quote it in the intent file"
        raise ValueError(msg)
    if not isinstance(value, str) or not MAC.fullmatch(value):
        msg = f"mac must look like 02:00:00:11:00:12, not {value!r}"
        raise ValueError(msg)
    return value


def _normalizer(device_type: str, name: str) -> Callable[..., Any]:
    function = getattr(platform(device_type), name, None)
    if function is None:
        msg = f"platform {device_type!r} has no {name} normalizer"
        raise IntentError(msg)
    return function  # type: ignore[no-any-return]


def _known(expected: Mapping[str, Any], fields: Collection[str]) -> dict[str, Any]:
    unknown = set(expected) - set(fields)
    if unknown or not expected:
        msg = f"expected must name some of {', '.join(fields)}, not {sorted(unknown)}"
        raise ValueError(msg)
    return dict(expected)


def _pick(state: Mapping[str, Any], fields: Collection[str], what: str) -> dict:
    missing = [name for name in fields if name not in state]
    if missing:
        msg = f"{what} has no {', '.join(missing)}"
        raise ValueError(msg)
    return {name: state[name] for name in fields}


def check_bridge_port(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    port: str,
    expected: Mapping[str, Any],
) -> IntentResult:
    """Compare `forwarding`, STP `role` and `edge` of one bridge port.

    `role` is `root`, `designated`, `alternate`, `backup` or `disabled`.
    Only the fields named in `expected` are compared.
    """
    expect(CHECKS["bridge_port"].expected, expected, "bridge_port")
    wanted = _known(expected, BRIDGE_PORT)
    normalize = _normalizer(device_type, "bridge_port")
    what = f"bridge port {bridge}/{port}"
    return compare(
        wanted, lambda: _pick(normalize(evidence, bridge, port), wanted, what)
    )


def check_bridge_ports(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    expected: list[str],
) -> IntentResult:
    """Compare the set of ports of a bridge. Both sides are sorted lists."""
    expect(CHECKS["bridge_ports"].expected, expected, "bridge_ports")
    normalize = _normalizer(device_type, "bridge_ports")
    return compare(sorted(expected), lambda: sorted(normalize(evidence, bridge)))


def check_stp_bridge(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    expected: Mapping[str, Any],
) -> IntentResult:
    """Compare spanning-tree bridge state.

    Bridge IDs read `0xPPPP.mac` in lower case. `root_port` is `None` on the
    root bridge. Only the fields named in `expected` are compared.
    """
    expect(CHECKS["stp_bridge"].expected, expected, "stp_bridge")
    wanted = _known(expected, STP_BRIDGE)
    normalize = _normalizer(device_type, "stp_bridge")
    what = f"bridge {bridge}"
    return compare(wanted, lambda: _pick(normalize(evidence, bridge), wanted, what))


def check_stp_mode(
    evidence: Mapping[str, Any], device_type: str, bridge: str, expected: str
) -> IntentResult:
    """Compare the spanning-tree protocol of a bridge, `none` when it is off."""
    expect(CHECKS["stp_mode"].expected, expected, "stp_mode")
    normalize = _normalizer(device_type, "stp_mode")
    return compare(expected, lambda: normalize(evidence, bridge))


def check_mlag(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    expected: Mapping[str, Any],
) -> IntentResult:
    """Compare MLAG peer state: `connected`, `role` and the platform's `state` word.

    `role` is `primary` or `secondary`. Only the fields named in `expected`
    are compared.
    """
    expect(CHECKS["mlag"].expected, expected, "mlag")
    wanted = _known(expected, MLAG)
    normalize = _normalizer(device_type, "mlag")
    what = f"MLAG on {bridge}"
    return compare(wanted, lambda: _pick(normalize(evidence, bridge), wanted, what))


def check_lacp_member(
    evidence: Mapping[str, Any],
    device_type: str,
    bond: str,
    member: str,
    expected: Mapping[str, bool],
) -> IntentResult:
    """Compare LACP state flags of a bond member on both the actor and partner side.

    For example `{"synchronization": True, "collecting": True,
    "distributing": True}`. The result holds `{"actor": ..., "partner": ...}`.
    """
    expect(CHECKS["lacp_member"].expected, expected, "lacp_member")
    wanted = _known(expected, LACP_FLAGS)
    normalize = _normalizer(device_type, "lacp_member")
    what = f"{bond} member {member}"

    def observe() -> dict[str, dict | None]:
        state = normalize(evidence, bond, member)
        # A member without an LACP partner, such as one that is down, fails.
        partner = state.get("partner")
        return {
            "actor": _pick(state["actor"], wanted, what),
            "partner": None if partner is None else _pick(partner, wanted, what),
        }

    return compare({"actor": wanted, "partner": wanted}, observe)


def check_lacp_actor(
    evidence: Mapping[str, Any],
    device_type: str,
    bond: str,
    member: str,
    expected: Mapping[str, bool],
) -> IntentResult:
    """Compare local LACP flags after the partner has timed out or while active."""
    expect(CHECKS["lacp_actor"].expected, expected, "lacp_actor")
    wanted = _known(expected, LACP_FLAGS)
    normalize = _normalizer(device_type, "lacp_member")
    what = f"{bond} member {member} actor"
    return compare(
        wanted, lambda: _pick(normalize(evidence, bond, member)["actor"], wanted, what)
    )


def check_lacp_partner_system(
    evidence: Mapping[str, Any],
    device_type: str,
    bond: str,
    member: str,
    expected: Mapping[str, Any],
) -> IntentResult:
    """Compare the LACP system `priority` and `mac` a bond member's partner sends.

    MLAG peers must present one system ID, so the partner of every member of
    an MLAG bond reports the same value.
    """
    expect(CHECKS["lacp_partner_system"].expected, expected, "lacp_partner_system")
    wanted = _known(expected, LACP_SYSTEM)
    normalize = _normalizer(device_type, "lacp_member")
    what = f"{bond} member {member} partner"

    def observe() -> dict[str, Any]:
        state = normalize(evidence, bond, member)
        if "partner_system" not in state:
            msg = "no LACP partner"
            raise ValueError(msg)
        return _pick(state["partner_system"], wanted, what)

    return compare(wanted, observe)


def check_bond_members(
    evidence: Mapping[str, Any], device_type: str, bond: str, expected: list[str]
) -> IntentResult:
    """Compare the member ports of a bond. Both sides are sorted lists."""
    expect(CHECKS["bond_members"].expected, expected, "bond_members")
    normalize = _normalizer(device_type, "bond_members")
    return compare(sorted(expected), lambda: sorted(normalize(evidence, bond)))


def check_host_entry(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    mac: str,
    expected: str | None,
) -> IntentResult:
    """Compare the port a bridge host table entry points to, `None` for no entry."""
    expect(CHECKS["host_entry"].expected, expected, "host_entry")
    normalize = _normalizer(device_type, "host_entry")
    return compare(expected, lambda: normalize(evidence, bridge, mac))


def check_interface_up(
    evidence: Mapping[str, Any],
    device_type: str,
    interface: str,
    *,
    expected: bool = True,
) -> IntentResult:
    """Compare whether an interface has carrier."""
    expect(CHECKS["interface_up"].expected, expected, "interface_up")
    normalize = _normalizer(device_type, "interface_up")
    return compare(expected, lambda: normalize(evidence, interface))


def check_ping(
    evidence: Mapping[str, Any],
    device_type: str,
    dest: str,
    count: int,
    interface: str | None,
    expected: Mapping[str, Any],
    *,
    vrf: str | None = None,
) -> IntentResult:
    """Compare a ping from the device: `sent`, `received` and `reachable`.

    `reachable` means every probe was answered. Only the fields named in
    `expected` are compared; a loss tolerance is not a field. `interface`
    and `vrf` are optional.
    """
    expect(CHECKS["ping"].expected, expected, "ping")
    wanted = _known(expected, PING)
    normalize = _normalizer(device_type, "ping")
    what = f"ping {dest}"
    return compare(
        wanted,
        lambda: _pick(normalize(evidence, dest, count, interface, vrf), wanted, what),
    )


# Intent files: run every item against the devices, save the evidence, replay it.

ITEM_KEYS = {"name", "device", "check", "params", "expected", "source"}
INTENT_FILE = "intent.yaml"
EVIDENCE_FILE = "evidence.json"
RESULTS_FILE = "results.json"
SCALARS = (str, int, bool, type(None))


def _menu(value: Any) -> str:
    if not isinstance(value, str) or not MENU.fullmatch(value):
        msg = f"menu must be a path such as /interface/bridge/port, not {value!r}"
        raise ValueError(msg)
    return value


def _property(value: Any) -> str:
    if not isinstance(value, str) or not PROPERTY.fullmatch(value):
        msg = f"property name must look like pvid or mlag-priority, not {value!r}"
        raise ValueError(msg)
    return value


def _where(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        msg = "where must be a non-empty mapping of property names to values"
        raise ValueError(msg)
    for key, item in value.items():
        _property(key)
        if not isinstance(item, str | int | bool) or isinstance(item, float):
            msg = f"where value of {key} must be a string, number or Boolean"
            raise ValueError(msg)
    return value


PARAMS: dict[str, Callable[[Any], Any]] = {
    "bridge": lambda v: name(v, "bridge"),
    "bond": lambda v: name(v, "bond"),
    "member": lambda v: name(v, "member"),
    "port": lambda v: name(v, "port"),
    "interface": lambda v: name(v, "interface"),
    "vrf": lambda v: name(v, "vrf"),
    "dest": address,
    "count": probes,
    "mac": mac,
    "menu": _menu,
    "where": _where,
    "name": _property,
}


def _type_names(types: tuple[type, ...]) -> str:
    names = {type(None): "null", list: "a list of those"}
    return " or ".join(names.get(t, t.__name__) for t in types)


def _json_native(value: Any, what: str = "expected") -> None:
    """Raise `ValueError` unless `value` is made of JSON strings, integers,
    Booleans, nulls, lists and string-keyed mappings; YAML dates and floats
    are not."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                msg = f"{what} has a key that is not a string: {key!r}"
                raise ValueError(msg)
            _json_native(item, f"{what} {key}")
    elif isinstance(value, list):
        for item in value:
            _json_native(item, what)
    elif type(value) not in SCALARS:
        msg = f"{what} must be a JSON string, integer, Boolean or null, not {value!r}"
        raise ValueError(msg)


def _expected(spec: Any, value: Any) -> None:
    """Raise `ValueError` unless `value` is JSON-native and fits the check's shape.

    `spec` is a tuple of allowed types (a list among them allows a list of
    the other types), a mapping of field to allowed types (some fields, each
    of its type), or a one-element list for a list of such values.
    """
    _json_native(value)
    if isinstance(spec, tuple):
        if isinstance(value, list) and list in spec:
            items, allowed = value, tuple(t for t in spec if t is not list)
        else:
            items, allowed = [value], spec
        if any(type(v) not in allowed for v in items):
            msg = f"expected must be {_type_names(spec)}, not {value!r}"
            raise ValueError(msg)
    elif isinstance(spec, list):
        if not isinstance(value, list) or any(type(v) not in spec[0] for v in value):
            msg = f"expected must be a list of {_type_names(spec[0])}"
            raise ValueError(msg)
    else:
        if not isinstance(value, dict) or not value:
            msg = f"expected must be a mapping of some of {', '.join(spec)}"
            raise ValueError(msg)
        for key, item in value.items():
            if key not in spec:
                msg = f"expected has unknown field {key!r}; known: {', '.join(spec)}"
                raise ValueError(msg)
            if type(item) not in spec[key]:
                msg = f"expected {key} must be {_type_names(spec[key])}, not {item!r}"
                raise ValueError(msg)


def expect(spec: Any, value: Any, check: str) -> None:
    """Validate `expected` of a direct check call as an intent file item is."""
    try:
        _expected(spec, value)
    except IntentError:
        raise
    except Exception as error:  # malformed input is the caller's error, named
        msg = f"{check}: {error}"
        raise IntentError(msg) from None


@dataclass(frozen=True, slots=True)
class Check:
    """How to collect and evaluate one named check.

    `collector` names a function of the platform module, called with the
    client, the device and every param in `params` order. `normalizer` names the
    platform normalizer a neutral check needs, `None` for a platform check.
    `expected` is the shape `expected` must have, as `_expected` reads it.
    `optional` params may be left out and reach the collector as `None`.
    """

    params: tuple[str, ...]
    collector: str
    evaluate: Callable[[Mapping[str, Any], str, Mapping[str, Any], Any], IntentResult]
    normalizer: str | None = None
    expected: Any = None
    optional: tuple[str, ...] = ()


_BOOL = (bool,)
_STR = (str,)

CHECKS: dict[str, Check] = {
    "bridge_port": Check(
        ("bridge", "port"),
        "collect_bridge_port",
        lambda ev, dt, p, e: check_bridge_port(ev, dt, p["bridge"], p["port"], e),
        "bridge_port",
        {"forwarding": _BOOL, "role": _STR, "edge": _BOOL},
    ),
    "bridge_ports": Check(
        ("bridge",),
        "collect_bridge",
        lambda ev, dt, p, e: check_bridge_ports(ev, dt, p["bridge"], e),
        "bridge_ports",
        [_STR],
    ),
    "stp_bridge": Check(
        ("bridge",),
        "collect_bridge",
        lambda ev, dt, p, e: check_stp_bridge(ev, dt, p["bridge"], e),
        "stp_bridge",
        {
            "bridge_id": _STR,
            "root_bridge_id": _STR,
            "root_bridge": _BOOL,
            "root_port": (str, type(None)),
            "topology_changes": (int,),
        },
    ),
    "stp_mode": Check(
        ("bridge",),
        "collect_stp_mode",
        lambda ev, dt, p, e: check_stp_mode(ev, dt, p["bridge"], e),
        "stp_mode",
        _STR,
    ),
    "mlag": Check(
        ("bridge",),
        "collect_bridge",
        lambda ev, dt, p, e: check_mlag(ev, dt, p["bridge"], e),
        "mlag",
        {"connected": _BOOL, "role": _STR, "state": _STR},
    ),
    "lacp_member": Check(
        ("bond", "member"),
        "collect_bond",
        lambda ev, dt, p, e: check_lacp_member(ev, dt, p["bond"], p["member"], e),
        "lacp_member",
        dict.fromkeys(LACP_FLAGS, _BOOL),
    ),
    "lacp_actor": Check(
        ("bond", "member"),
        "collect_bond",
        lambda ev, dt, p, e: check_lacp_actor(ev, dt, p["bond"], p["member"], e),
        "lacp_member",
        dict.fromkeys(LACP_FLAGS, _BOOL),
    ),
    "lacp_partner_system": Check(
        ("bond", "member"),
        "collect_bond",
        lambda ev, dt, p, e: check_lacp_partner_system(
            ev, dt, p["bond"], p["member"], e
        ),
        "lacp_member",
        {"priority": (int,), "mac": _STR},
    ),
    "bond_members": Check(
        ("bond",),
        "collect_bond",
        lambda ev, dt, p, e: check_bond_members(ev, dt, p["bond"], e),
        "bond_members",
        [_STR],
    ),
    "host_entry": Check(
        ("bridge", "mac"),
        "collect_host_entry",
        lambda ev, dt, p, e: check_host_entry(ev, dt, p["bridge"], p["mac"], e),
        "host_entry",
        (str, type(None)),
    ),
    "interface_up": Check(
        ("interface",),
        "collect_interface",
        lambda ev, dt, p, e: check_interface_up(ev, dt, p["interface"], expected=e),
        "interface_up",
        _BOOL,
    ),
    "ping": Check(
        ("dest", "count"),
        "collect_ping",
        lambda ev, dt, p, e: check_ping(
            ev, dt, p["dest"], p["count"], p.get("interface"), e, vrf=p.get("vrf")
        ),
        "ping",
        {"reachable": _BOOL, "received": (int,)},
        ("interface", "vrf"),
    ),
}


@dataclass(frozen=True, slots=True)
class IntentItem:
    """One item of an intent file. `where` names the file and item for errors."""

    device: str
    check: str
    expected: Any
    params: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
    source: str | None = None
    where: str = field(default="", compare=False)

    def to_yaml(self) -> dict[str, Any]:
        """The item as written to an intent file."""
        item: dict[str, Any] = {"name": self.name} if self.name is not None else {}
        item |= {"device": self.device, "check": self.check}
        if self.params:
            item["params"] = self.params
        item["expected"] = self.expected
        if self.source is not None:
            item["source"] = self.source
        return item


@dataclass(frozen=True, slots=True)
class IntentReport:
    """Results in item order, the overall verdict and the evidence they came from."""

    verdict: Verdict
    results: list[tuple[IntentItem, IntentResult]]
    evidence: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        """The content of `results.json`."""
        items = [
            {
                "name": item.name,
                "source": item.source,
                "device": item.device,
                "check": item.check,
                "expected": result.expected,
                "observed": result.observed,
                "verdict": result.verdict,
                "reason": result.reason,
            }
            for item, result in self.results
        ]
        return {"verdict": self.verdict, "items": items}


_CLAIMED: dict[str, tuple[str, Check]] = {}


def claim(platform_name: str, checks: Mapping[str, Check]) -> None:
    """Record a platform's own checks; called at the end of each platform module.

    Check names share one namespace across platforms. A name may appear on
    several platforms only with the same params, optional params and
    expected shape, and never as a neutral check name, so an intent file
    means the same thing on every platform. A conflict fails at import.
    """
    for check_name, check in checks.items():
        if check_name in CHECKS:
            msg = f"{platform_name} check {check_name!r} reuses a neutral check name"
            raise IntentError(msg)
        owner = _CLAIMED.get(check_name)
        contract = (check.params, check.optional, check.expected)
        if (
            owner is not None
            and (owner[1].params, owner[1].optional, owner[1].expected) != contract
        ):
            msg = (
                f"{platform_name} check {check_name!r} differs from the "
                f"{owner[0]} check of that name"
            )
            raise IntentError(msg)
        _CLAIMED.setdefault(check_name, (platform_name, check))


def _platform_checks() -> dict[str, dict[str, Check]]:
    return {name: platform(name).CHECKS for name in PLATFORMS}


def _definition(check: str) -> Check | None:
    """The check of this name, neutral or of any platform."""
    if check in CHECKS:
        return CHECKS[check]
    found = [checks[check] for checks in _platform_checks().values() if check in checks]
    return found[0] if found else None


def validate_intent(intent: Any) -> list[Check]:
    """Validate a whole intent; the one validation path for files and Python.

    `load_intent`, `run_intent` and `replay_intent` all call it. An intent
    must be a non-empty list of items. Any failure, including one Python
    raises on malformed input, is an `IntentError` that names the item.
    """
    if not isinstance(intent, list) or not intent:
        msg = "an intent must be a non-empty list of items"
        raise IntentError(msg)
    checks = []
    for number, item in enumerate(intent, 1):
        where = getattr(item, "where", "") or f"item {number}"
        try:
            checks.append(validate(item))
        except IntentError:
            raise
        except Exception as error:  # malformed input: name the item, never a traceback
            msg = f"{where}: invalid item: {type(error).__name__}: {error}"
            raise IntentError(msg) from None
    return checks


def validate(item: IntentItem) -> Check:
    """Check one item's check name, params and expected.

    `params` must be a mapping; an absent `params` in a file is an empty one.
    """
    if not isinstance(item, IntentItem):
        msg = f"an intent item must be an IntentItem, not {type(item).__name__}"
        raise IntentError(msg)
    check = _definition(item.check) if isinstance(item.check, str) else None
    if check is None:
        known = set(CHECKS) | {c for cs in _platform_checks().values() for c in cs}
        msg = f"{item.where}: unknown check {item.check!r}; known: {', '.join(sorted(known))}"
        raise IntentError(msg)
    if not isinstance(item.device, str) or not item.device:
        msg = f"{item.where}: device must be a name"
        raise IntentError(msg)
    for key in ("name", "source"):
        if getattr(item, key) is not None and not isinstance(getattr(item, key), str):
            msg = f"{item.where}: {key} must be a string"
            raise IntentError(msg)
    if not isinstance(item.params, dict):
        msg = f"{item.where}: params must be a mapping, not {item.params!r}"
        raise IntentError(msg)
    if not set(check.params) <= set(item.params) <= {*check.params, *check.optional}:
        takes = [*check.params, *(f"{key} (optional)" for key in check.optional)]
        msg = f"{item.where}: {item.check} takes params {takes}, not {item.params!r}"
        raise IntentError(msg)
    try:
        for key, value in item.params.items():
            PARAMS[key](value)
        _expected(check.expected, item.expected)
    except ValueError as error:
        msg = f"{item.where}: {error}"
        raise IntentError(msg) from None
    return check


def load_intent(path: str | Path) -> list[IntentItem]:
    """Read and strictly validate an intent file: a YAML list of items.

    Keys, check names, params (names, MAC addresses, menus) and the shape of
    `expected` are all checked here, before any device is read.
    """
    path = Path(path)
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)  # noqa: S506 - a SafeLoader subclass
    except (OSError, yaml.YAMLError) as error:
        msg = f"{path}: cannot read the intent file: {error}"
        raise IntentError(msg) from None
    if not isinstance(data, list) or not data:
        msg = f"{path}: the intent file must be a non-empty list of items"
        raise IntentError(msg)
    items = [parse_item(raw, f"{path} item {n}") for n, raw in enumerate(data, 1)]
    validate_intent(items)
    return items


def parse_item(raw: Any, where: str) -> IntentItem:
    """One intent item from its YAML mapping; `where` names it in errors.

    Only the keys are checked here. `validate_intent` checks the rest.
    """
    if not isinstance(raw, dict):
        msg = f"{where}: an item must be a mapping"
        raise IntentError(msg)
    if isinstance(raw.get("name"), str):
        where += f" ({raw['name']})"
    if unknown := set(raw) - ITEM_KEYS:
        names = sorted(map(repr, unknown))
        msg = f"{where}: unknown keys {', '.join(names)}; allowed: {sorted(ITEM_KEYS)}"
        raise IntentError(msg)
    if missing := {"device", "check", "expected"} - set(raw):
        msg = f"{where}: missing keys {sorted(missing)}"
        raise IntentError(msg)
    if not isinstance(raw["device"], str) or not isinstance(raw["check"], str):
        msg = f"{where}: device and check must be strings"
        raise IntentError(msg)
    return IntentItem(
        raw["device"],
        raw["check"],
        raw["expected"],
        raw.get("params", {}),
        raw.get("name"),
        raw.get("source"),
        where,
    )


def _resolve(item: IntentItem, device_type: str) -> Check:
    """The check for this item on this platform, or an error naming the item."""
    try:
        module = platform(device_type)
    except IntentError as error:
        msg = f"{item.where}: device {item.device}: {error.message}"
        raise IntentError(msg) from None
    check = CHECKS.get(item.check) or module.CHECKS.get(item.check)
    if check is None:
        owners = [n for n, checks in _platform_checks().items() if item.check in checks]
        msg = f"{item.where}: check {item.check!r} is only for {', '.join(owners)}, not {device_type}"
        raise IntentError(msg)
    for name_ in (check.collector, check.normalizer):
        if name_ is not None and not hasattr(module, name_):
            msg = f"{item.where}: {device_type} does not support {item.check} (no {name_})"
            raise IntentError(msg)
    # A platform may restrict how params combine, for example Linux ping.
    rule = getattr(module, "PARAM_RULES", {}).get(item.check)
    if rule is not None:
        try:
            rule(item.params)
        except ValueError as error:
            msg = f"{item.where}: {device_type}: {error}"
            raise IntentError(msg) from None
    return check


def _reading(check: Check, item: IntentItem) -> dict[str, Any]:
    """The key of the one reading an item needs: collector and its arguments.

    Optional params that are not given are left off the end of `args`, so
    the collector gets its defaults and adding an optional param keeps
    existing keys.
    """
    args = [item.params.get(key) for key in (*check.params, *check.optional)]
    return {"collector": check.collector, "args": _trim(args, check)}


def _trim(args: Any, check: Check) -> Any:
    """`args` without trailing `None` optional params; other values unchanged."""
    if not isinstance(args, list):
        return args
    args = list(args)
    while len(args) > len(check.params) and args[-1] is None:
        args.pop()
    return args


def _rollup(results: list[IntentResult]) -> Verdict:
    verdicts = {result.verdict for result in results}
    return "fail" if "fail" in verdicts else "error" if "error" in verdicts else "pass"


def _evaluate(item: IntentItem, saved: Any) -> IntentResult:
    """One item from the saved evidence of its device; never raises."""

    def error(reason: str) -> IntentResult:
        return IntentResult(item.expected, None, "error", reason)

    if not isinstance(saved, dict) or not isinstance(saved.get("device_type"), str):
        return error(f"no evidence for device {item.device}")
    try:
        check = _resolve(item, saved["device_type"])
    except IntentError as failure:
        return error(failure.message)
    key = _reading(check, item)
    readings = saved.get("readings")
    if not isinstance(readings, list):
        return error(f"the evidence of {item.device} has no list of readings")
    matching = [
        r
        for r in readings
        if isinstance(r, dict)
        and same(
            key,
            {"collector": r.get("collector"), "args": _trim(r.get("args"), check)},
        )
    ]
    if len(matching) == 1 and "error" in matching[0]:
        # A reading whose collection recorded any error decides no item that
        # uses it; a successful reading has no error key.
        failed = matching[0]["error"]
        return error(
            failed
            if isinstance(failed, str) and failed
            else f"reading error: {failed!r}"
        )
    found = [r.get("replies") for r in matching]
    if len(found) != 1 or not isinstance(found[0], dict):
        return error(
            f"expected one {key['collector']} reading of {item.device}, found {len(found)}"
        )
    try:
        return check.evaluate(
            found[0], saved["device_type"], item.params, item.expected
        )
    except Exception as failure:  # any failure is this item's error
        return error(f"{type(failure).__name__}: {failure}")


def replay_intent(intent: list[IntentItem], evidence: Any) -> IntentReport:
    """Evaluate every item from saved evidence, without devices.

    `evidence` is the content of `evidence.json` written by `run_intent`. An
    item whose device or reading is missing or malformed gives `error`.
    """
    validate_intent(intent)
    devices = evidence.get("devices") if isinstance(evidence, Mapping) else None
    if not isinstance(devices, dict):
        msg = "the evidence has no devices"
        raise IntentError(msg)
    results = [(item, _evaluate(item, devices.get(item.device))) for item in intent]
    return IntentReport(_rollup([r for _, r in results]), results, dict(evidence))


def _connection_failure(device: str, replies: Mapping[str, Any]) -> str | None:
    """The error of a reading whose device did not accept a connection, else `None`.

    `DeviceSession` reports that as "Connection failed for <device>: ...".
    """
    prefix = f"Connection failed for {device}:"
    for reply in replies.values():
        error = reply.get("error") if isinstance(reply, dict) else None
        if isinstance(error, str) and error.startswith(prefix):
            return error
    return None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _device_type(client: NetworkaClient, item: IntentItem) -> str:
    """The device type from the inventory, resolved as the command API does."""
    config = client.config
    try:
        kind = select_named_target(config, item.device)
    except NetworkToolkitError as failure:
        msg = f"{item.where}: device {item.device!r}: {failure.message}"
        raise IntentError(msg) from None
    device = (config.devices or {}).get(item.device) if kind == "device" else None
    if device is None:
        msg = f"{item.where}: device {item.device!r} is not in the inventory"
        raise IntentError(msg)
    if not device.device_type:
        msg = (
            f"{item.where}: device {item.device!r} has no device_type in the inventory"
        )
        raise IntentError(msg)
    return device.device_type


def run_intent(
    client: NetworkaClient,
    intent: list[IntentItem],
    save_dir: str | Path | None = None,
    **run_options: Any,
) -> IntentReport:
    """Collect every reading once, then evaluate it exactly as `replay_intent` does.

    Every item is resolved against the inventory before any device is read.
    Items that need the same collector with the same arguments on one device
    share one reading. With `save_dir`, `intent.yaml` is written from the
    validated items before collecting, and `evidence.json` and `results.json`
    after. `run_options` are passed to `NetworkaClient.run`.
    """
    plan: dict[str, dict[str, Any]] = {}
    validate_intent(intent)
    for item in intent:
        device_type = _device_type(client, item)
        key = _reading(_resolve(item, device_type), item)
        device = plan.setdefault(
            item.device, {"device_type": device_type, "readings": []}
        )
        if not any(same(key, {k: r[k] for k in key}) for r in device["readings"]):
            device["readings"].append(key)
    folder = Path(save_dir) if save_dir is not None else None
    if folder is not None:
        folder.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump([item.to_yaml() for item in intent], sort_keys=False)
        (folder / INTENT_FILE).write_text(text)
    for device_name, device in plan.items():
        module = platform(device["device_type"])
        device["started"] = _now()
        unreachable = None
        for reading in device["readings"]:
            if unreachable is not None:
                # The device did not accept a connection: do not wait for it again.
                reading["replies"], reading["error"] = {}, unreachable
                continue
            collect = getattr(module, reading["collector"])
            try:
                reading["replies"] = collect(
                    client, device_name, *reading["args"], **run_options
                )
            except Exception as failure:  # any collector failure is kept as evidence
                reading["replies"] = {}
                reading["error"] = f"{type(failure).__name__}: {failure}"
                continue
            unreachable = _connection_failure(device_name, reading["replies"])
        device["finished"] = _now()
    evidence = {"networka_version": __version__, "devices": plan}
    report = replay_intent(intent, evidence)
    if folder is not None:
        (folder / EVIDENCE_FILE).write_text(json.dumps(evidence, indent=2) + "\n")
        (folder / RESULTS_FILE).write_text(
            json.dumps(report.to_json(), indent=2) + "\n"
        )
    return report


def replay_directory(folder: str | Path) -> IntentReport:
    """Replay a directory written by `run_intent`: `intent.yaml` and `evidence.json`."""
    folder = Path(folder)
    intent = load_intent(folder / INTENT_FILE)
    try:
        evidence = load_json((folder / EVIDENCE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        msg = f"{folder / EVIDENCE_FILE}: cannot read the evidence: {error}"
        raise IntentError(msg) from None
    return replay_intent(intent, evidence)
