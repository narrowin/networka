# SPDX-License-Identifier: MIT
"""Vendor-neutral intent checks over saved device evidence.

A platform module collects replies through `NetworkaClient.run` and keeps
each one as a `Reply`. Its normalizers turn that evidence into neutral fields,
or raise `ValueError` when the evidence cannot decide. The checks here compare
those fields with the expectation and never see command text, so saved
evidence replays to the same verdict without the device.

`platform(device_type)` selects the module for a Networka device type.
"""

from __future__ import annotations

import importlib
import json
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict

import yaml

from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from collections.abc import Collection
    from types import ModuleType

    from network_toolkit.client import NetworkaClient

Verdict = Literal["match", "mismatch", "unavailable"]

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


class Reply(TypedDict):
    """One command with its device output or error, as saved for replay."""

    command: str
    output: str | None
    error: str | None


@dataclass(frozen=True, slots=True)
class IntentResult:
    """Expected and observed value with the verdict.

    `unavailable` means the evidence cannot decide the check. `reason` says why.
    """

    expected: Any
    observed: Any
    verdict: Verdict
    reason: str | None = None


def platform(device_type: str) -> ModuleType:
    """Return the collectors and normalizers for a Networka device type."""
    if device_type not in PLATFORMS:
        supported = ", ".join(sorted(PLATFORMS))
        msg = f"no intent checks for platform {device_type!r}; supported: {supported}"
        raise NetworkToolkitError(msg)
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
    evidence: Mapping[str, Any], accepts: Callable[[str], bool], what: str
) -> str:
    """Return the output of the one reply whose command `accepts` selects."""
    replies = [
        reply
        for reply in evidence.values()
        if isinstance(reply, dict)
        and isinstance(reply.get("command"), str)
        and accepts(reply["command"])
    ]
    if len(replies) != 1:
        msg = f"expected one reply for {what} in the evidence, found {len(replies)}"
        raise ValueError(msg)
    if replies[0].get("error"):
        raise ValueError(str(replies[0]["error"]))
    output = replies[0].get("output")
    if not isinstance(output, str):
        msg = f"reply for {what} has no output"
        raise ValueError(msg)
    return output


def _normalizer(device_type: str, name: str) -> Callable[..., Any]:
    function = getattr(platform(device_type), name, None)
    if function is None:
        msg = f"platform {device_type!r} has no {name} normalizer"
        raise NetworkToolkitError(msg)
    return function  # type: ignore[no-any-return]


def _known(expected: Mapping[str, Any], fields: Collection[str]) -> dict[str, Any]:
    unknown = set(expected) - set(fields)
    if unknown or not expected:
        msg = f"expected must name some of {', '.join(fields)}, not {sorted(unknown)}"
        raise ValueError(msg)
    return dict(expected)


def _pick(state: Mapping[str, Any], fields: Collection[str], what: str) -> dict:
    missing = [field for field in fields if field not in state]
    if missing:
        msg = f"{what} has no {', '.join(missing)}"
        raise ValueError(msg)
    return {field: state[field] for field in fields}


def _compare(expected: Any, observe: Callable[[], Any]) -> IntentResult:
    try:
        observed = observe()
    except ValueError as error:
        return IntentResult(expected, None, "unavailable", str(error))
    verdict: Verdict = "match" if observed == expected else "mismatch"
    return IntentResult(expected, observed, verdict)


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
    wanted = _known(expected, BRIDGE_PORT)
    normalize = _normalizer(device_type, "bridge_port")
    what = f"bridge port {bridge}/{port}"
    return _compare(
        wanted, lambda: _pick(normalize(evidence, bridge, port), wanted, what)
    )


def check_bridge_port_forwarding(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    port: str,
    *,
    expected: bool = True,
) -> IntentResult:
    """Compare the forwarding Boolean of one bridge port."""
    normalize = _normalizer(device_type, "bridge_port")
    what = f"bridge port {bridge}/{port}"
    return _compare(
        expected,
        lambda: _pick(normalize(evidence, bridge, port), ["forwarding"], what)[
            "forwarding"
        ],
    )


def check_bridge_ports(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    expected: Collection[str],
) -> IntentResult:
    """Compare the set of ports of a bridge. Both sides are sorted lists."""
    normalize = _normalizer(device_type, "bridge_ports")
    return _compare(sorted(expected), lambda: sorted(normalize(evidence, bridge)))


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
    wanted = _known(expected, STP_BRIDGE)
    normalize = _normalizer(device_type, "stp_bridge")
    return _compare(
        wanted, lambda: _pick(normalize(evidence, bridge), wanted, f"bridge {bridge}")
    )


def check_stp_mode(
    evidence: Mapping[str, Any], device_type: str, bridge: str, expected: str
) -> IntentResult:
    """Compare the spanning-tree protocol of a bridge, `none` when it is off."""
    normalize = _normalizer(device_type, "stp_mode")
    return _compare(expected, lambda: normalize(evidence, bridge))


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
    wanted = _known(expected, MLAG)
    normalize = _normalizer(device_type, "mlag")
    return _compare(
        wanted, lambda: _pick(normalize(evidence, bridge), wanted, f"MLAG on {bridge}")
    )


def check_lacp_member(
    evidence: Mapping[str, Any],
    device_type: str,
    bond: str,
    member: str,
    expected: Mapping[str, bool],
) -> IntentResult:
    """Compare LACP state flags of a bond member on both the actor and partner side.

    For example `{"synchronization": True, "collecting": True,
    "distributing": True}`. Observed is `{"actor": {...}, "partner": {...}}`.
    """
    wanted = _known(expected, LACP_FLAGS)
    normalize = _normalizer(device_type, "lacp_member")
    what = f"{bond} member {member}"

    def observe() -> dict[str, dict]:
        state = normalize(evidence, bond, member)
        return {side: _pick(state[side], wanted, what) for side in ("actor", "partner")}

    try:
        observed = observe()
    except ValueError as error:
        return IntentResult(wanted, None, "unavailable", str(error))
    same = observed["actor"] == wanted and observed["partner"] == wanted
    return IntentResult(wanted, observed, "match" if same else "mismatch")


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
    wanted = _known(expected, LACP_SYSTEM)
    normalize = _normalizer(device_type, "lacp_member")
    what = f"{bond} member {member} partner"
    return _compare(
        wanted,
        lambda: _pick(
            normalize(evidence, bond, member)["partner_system"], wanted, what
        ),
    )


def check_host_entry(
    evidence: Mapping[str, Any],
    device_type: str,
    bridge: str,
    mac: str,
    expected: str | None,
) -> IntentResult:
    """Compare the port a bridge host table entry points to, `None` for no entry."""
    normalize = _normalizer(device_type, "host_interface")
    return _compare(expected, lambda: normalize(evidence, bridge, mac))


def check_interface_up(
    evidence: Mapping[str, Any],
    device_type: str,
    interface: str,
    *,
    expected: bool = True,
) -> IntentResult:
    """Compare whether an interface has carrier."""
    normalize = _normalizer(device_type, "interface_up")
    return _compare(expected, lambda: normalize(evidence, interface))


def check_rebooted(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    device_type: str,
    *,
    expected: bool = True,
) -> IntentResult:
    """Compare whether the uptime went down between two readings."""
    normalize = _normalizer(device_type, "uptime_ns")
    return _compare(expected, lambda: normalize(after) < normalize(before))


# Intent files: run every item against the devices, save the evidence, replay it.

Rollup = Literal["pass", "fail", "unverified"]
ITEM_KEYS = {"name", "device", "check", "params", "expected", "source"}
INTENT_FILE = "intent.yaml"
EVIDENCE_FILE = "evidence.json"


class IntentError(NetworkToolkitError):
    """An intent file, its evidence, or an item cannot be used."""


@dataclass(frozen=True, slots=True)
class Check:
    """How to collect and evaluate one named check.

    `collector` names a function of the platform module, called with the
    client, the device and the `collect_args` params. `normalizer` names the
    platform normalizer a neutral check needs, `None` for a platform check.
    """

    params: tuple[str, ...]
    collector: str
    collect_args: tuple[str, ...]
    evaluate: Callable[[Mapping[str, Any], str, Mapping[str, Any], Any], IntentResult]
    normalizer: str | None = None


CHECKS: dict[str, Check] = {
    "bridge_port": Check(
        ("bridge", "port"),
        "collect_bridge_port",
        ("bridge", "port"),
        lambda ev, dt, p, e: check_bridge_port(ev, dt, p["bridge"], p["port"], e),
        "bridge_port",
    ),
    "bridge_port_forwarding": Check(
        ("bridge", "port"),
        "collect_bridge_port",
        ("bridge", "port"),
        lambda ev, dt, p, e: check_bridge_port_forwarding(
            ev, dt, p["bridge"], p["port"], expected=e
        ),
        "bridge_port",
    ),
    "bridge_ports": Check(
        ("bridge",),
        "collect_bridge",
        ("bridge",),
        lambda ev, dt, p, e: check_bridge_ports(ev, dt, p["bridge"], e),
        "bridge_ports",
    ),
    "stp_bridge": Check(
        ("bridge",),
        "collect_bridge",
        ("bridge",),
        lambda ev, dt, p, e: check_stp_bridge(ev, dt, p["bridge"], e),
        "stp_bridge",
    ),
    "stp_mode": Check(
        ("bridge",),
        "collect_stp_mode",
        ("bridge",),
        lambda ev, dt, p, e: check_stp_mode(ev, dt, p["bridge"], e),
        "stp_mode",
    ),
    "mlag": Check(
        ("bridge",),
        "collect_bridge",
        ("bridge",),
        lambda ev, dt, p, e: check_mlag(ev, dt, p["bridge"], e),
        "mlag",
    ),
    "lacp_member": Check(
        ("bond", "member"),
        "collect_bond",
        ("bond",),
        lambda ev, dt, p, e: check_lacp_member(ev, dt, p["bond"], p["member"], e),
        "lacp_member",
    ),
    "lacp_partner_system": Check(
        ("bond", "member"),
        "collect_bond",
        ("bond",),
        lambda ev, dt, p, e: check_lacp_partner_system(
            ev, dt, p["bond"], p["member"], e
        ),
        "lacp_member",
    ),
    "host_entry": Check(
        ("bridge", "mac"),
        "collect_host_entry",
        ("mac",),
        lambda ev, dt, p, e: check_host_entry(ev, dt, p["bridge"], p["mac"], e),
        "host_interface",
    ),
    "interface_up": Check(
        ("interface",),
        "collect_interface",
        ("interface",),
        lambda ev, dt, p, e: check_interface_up(ev, dt, p["interface"], expected=e),
        "interface_up",
    ),
}


@dataclass(frozen=True, slots=True)
class IntentItem:
    """One line of an intent file. `where` names the file and item for errors."""

    device: str
    check: str
    params: dict[str, Any]
    expected: Any
    name: str | None = None
    source: str | None = None
    where: str = ""


@dataclass(frozen=True, slots=True)
class IntentReport:
    """Results in item order, the roll-up verdict and the evidence they came from."""

    verdict: Rollup
    results: list[tuple[IntentItem, IntentResult]]
    evidence: dict[str, Any]


def _platform_checks() -> dict[str, dict[str, Check]]:
    return {name: platform(name).CHECKS for name in PLATFORMS}


def load_intent(path: str | Path) -> list[IntentItem]:
    """Read and strictly validate an intent file: a YAML list of items."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        msg = f"{path}: cannot read the intent file: {error}"
        raise IntentError(msg) from None
    if not isinstance(data, list) or not data:
        msg = f"{path}: the intent file must be a non-empty list of items"
        raise IntentError(msg)
    known = set(CHECKS) | {
        check for checks in _platform_checks().values() for check in checks
    }
    items = []
    for number, raw in enumerate(data, 1):
        where = f"{path} item {number}"
        if not isinstance(raw, dict):
            msg = f"{where}: an item must be a mapping"
            raise IntentError(msg)
        if isinstance(raw.get("name"), str):
            where += f" ({raw['name']})"
        if unknown := set(raw) - ITEM_KEYS:
            msg = (
                f"{where}: unknown keys {sorted(unknown)}; allowed: {sorted(ITEM_KEYS)}"
            )
            raise IntentError(msg)
        if missing := {"device", "check", "params", "expected"} - set(raw):
            msg = f"{where}: missing keys {sorted(missing)}"
            raise IntentError(msg)
        if not isinstance(raw["device"], str) or not isinstance(raw["check"], str):
            msg = f"{where}: device and check must be strings"
            raise IntentError(msg)
        if raw["check"] not in known:
            msg = f"{where}: unknown check {raw['check']!r}; known: {', '.join(sorted(known))}"
            raise IntentError(msg)
        if not isinstance(raw["params"], dict):
            msg = f"{where}: params must be a mapping"
            raise IntentError(msg)
        for key in ("name", "source"):
            if raw.get(key) is not None and not isinstance(raw[key], str):
                msg = f"{where}: {key} must be a string"
                raise IntentError(msg)
        items.append(
            IntentItem(
                raw["device"],
                raw["check"],
                dict(raw["params"]),
                raw["expected"],
                raw.get("name"),
                raw.get("source"),
                where,
            )
        )
    return items


def _resolve(item: IntentItem, device_type: str) -> Check:
    """The check for this item on this platform, or an error naming the item."""
    try:
        module = platform(device_type)
    except NetworkToolkitError as error:
        msg = f"{item.where}: device {item.device}: {error.message}"
        raise IntentError(msg) from None
    check = CHECKS.get(item.check) or module.CHECKS.get(item.check)
    if check is None:
        owners = [
            name for name, checks in _platform_checks().items() if item.check in checks
        ]
        msg = f"{item.where}: check {item.check!r} is only for {', '.join(owners)}, not {device_type}"
        raise IntentError(msg)
    if set(item.params) != set(check.params):
        msg = f"{item.where}: {item.check} takes params {list(check.params)}, not {sorted(item.params)}"
        raise IntentError(msg)
    for name in (check.collector, check.normalizer):
        if name is not None and not hasattr(module, name):
            msg = (
                f"{item.where}: {device_type} does not support {item.check} (no {name})"
            )
            raise IntentError(msg)
    return check


def _rollup(results: list[IntentResult]) -> Rollup:
    verdicts = {result.verdict for result in results}
    if "mismatch" in verdicts:
        return "fail"
    return "unverified" if "unavailable" in verdicts else "pass"


def replay_intent(
    intent: list[IntentItem], evidence: Mapping[str, Any]
) -> IntentReport:
    """Evaluate every item from saved evidence, without devices.

    `evidence` is the content of the evidence file written by `run_intent`.
    """
    saved = evidence.get("items") if isinstance(evidence, Mapping) else None
    if not isinstance(saved, list) or len(saved) != len(intent):
        msg = f"the evidence must hold one entry per intent item ({len(intent)})"
        raise IntentError(msg)
    results = []
    for item, entry in zip(intent, saved, strict=True):
        if not isinstance(entry, dict) or (entry.get("device"), entry.get("check")) != (
            item.device,
            item.check,
        ):
            msg = f"{item.where}: the evidence entry is for another device or check"
            raise IntentError(msg)
        device_type = entry.get("device_type")
        replies = entry.get("evidence")
        if not isinstance(device_type, str) or not isinstance(replies, dict):
            msg = f"{item.where}: the evidence entry has no device_type or evidence"
            raise IntentError(msg)
        check = _resolve(item, device_type)
        results.append(
            (item, check.evaluate(replies, device_type, item.params, item.expected))
        )
    return IntentReport(
        _rollup([result for _, result in results]), results, dict(evidence)
    )


def run_intent(
    client: NetworkaClient,
    intent: list[IntentItem],
    save_dir: str | Path | None = None,
    source: str | Path | None = None,
    **run_options: Any,
) -> IntentReport:
    """Collect every item from its device, then evaluate it as `replay_intent` does.

    The device type comes from the client's inventory. Every item is checked
    before any device is read. With `save_dir`, the directory receives
    `evidence.json` and, when `source` names the intent file, a copy of it as
    `intent.yaml`. `run_options` are passed to `NetworkaClient.run`.
    """
    plans = []
    for item in intent:
        config = client.devices.get(item.device)
        if config is None or not config.device_type:
            msg = f"{item.where}: device {item.device!r} is not in the inventory"
            raise IntentError(msg)
        plans.append((item, config.device_type, _resolve(item, config.device_type)))
    entries = []
    for item, device_type, check in plans:
        collect = getattr(platform(device_type), check.collector)
        args = [item.params[name] for name in check.collect_args]
        replies = collect(client, item.device, *args, **run_options)
        entries.append(
            {
                "device": item.device,
                "device_type": device_type,
                "check": item.check,
                "evidence": replies,
            }
        )
    evidence = {"items": entries}
    if save_dir is not None:
        folder = Path(save_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / EVIDENCE_FILE).write_text(json.dumps(evidence, indent=2) + "\n")
        if source is not None:
            shutil.copyfile(source, folder / INTENT_FILE)
    return replay_intent(intent, evidence)


def replay_directory(folder: str | Path) -> IntentReport:
    """Replay a directory written by `run_intent`: `intent.yaml` and `evidence.json`."""
    folder = Path(folder)
    intent = load_intent(folder / INTENT_FILE)
    try:
        evidence = json.loads((folder / EVIDENCE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        msg = f"{folder / EVIDENCE_FILE}: cannot read the evidence: {error}"
        raise IntentError(msg) from None
    return replay_intent(intent, evidence)
