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
import json
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict

import yaml

from network_toolkit.__about__ import __version__
from network_toolkit.exceptions import NetworkToolkitError

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
    if reply.get("error"):
        raise ValueError(str(reply["error"]))
    if reply.get("command") != (key if command is None else command):
        msg = f"{key} reply is for a different command"
        raise ValueError(msg)
    output = reply.get("output")
    if not isinstance(output, str):
        msg = f"{key} reply has no output"
        raise ValueError(msg)
    return output


def compare(expected: Any, observe: Callable[[], Any]) -> IntentResult:
    """`pass` when the observed value equals `expected`, `error` on `ValueError`."""
    try:
        observed = observe()
    except ValueError as error:
        return IntentResult(expected, None, "error", str(error))
    return IntentResult(expected, observed, "pass" if observed == expected else "fail")


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
    expected: Collection[str],
) -> IntentResult:
    """Compare the set of ports of a bridge. Both sides are sorted lists."""
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
    wanted = _known(expected, STP_BRIDGE)
    normalize = _normalizer(device_type, "stp_bridge")
    what = f"bridge {bridge}"
    return compare(wanted, lambda: _pick(normalize(evidence, bridge), wanted, what))


def check_stp_mode(
    evidence: Mapping[str, Any], device_type: str, bridge: str, expected: str
) -> IntentResult:
    """Compare the spanning-tree protocol of a bridge, `none` when it is off."""
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
    wanted = _known(expected, LACP_FLAGS)
    normalize = _normalizer(device_type, "lacp_member")
    what = f"{bond} member {member}"

    def observe() -> dict[str, dict]:
        state = normalize(evidence, bond, member)
        return {side: _pick(state[side], wanted, what) for side in ("actor", "partner")}

    return compare({"actor": wanted, "partner": wanted}, observe)


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
    return compare(
        wanted,
        lambda: _pick(
            normalize(evidence, bond, member).get("partner_system", {}), wanted, what
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
    return compare(expected, lambda: normalize(evidence, bridge, mac))


def check_interface_up(
    evidence: Mapping[str, Any],
    device_type: str,
    interface: str,
    *,
    expected: bool = True,
) -> IntentResult:
    """Compare whether an interface has carrier."""
    normalize = _normalizer(device_type, "interface_up")
    return compare(expected, lambda: normalize(evidence, interface))


# Intent files: run every item against the devices, save the evidence, replay it.

ITEM_KEYS = {"name", "device", "check", "params", "expected", "source"}
INTENT_FILE = "intent.yaml"
EVIDENCE_FILE = "evidence.json"
RESULTS_FILE = "results.json"


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
    """One item of an intent file. `where` names the file and item for errors."""

    device: str
    check: str
    expected: Any
    params: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
    source: str | None = None
    where: str = ""


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
        if missing := {"device", "check", "expected"} - set(raw):
            msg = f"{where}: missing keys {sorted(missing)}"
            raise IntentError(msg)
        if not isinstance(raw["device"], str) or not isinstance(raw["check"], str):
            msg = f"{where}: device and check must be strings"
            raise IntentError(msg)
        if raw["check"] not in known:
            msg = f"{where}: unknown check {raw['check']!r}; known: {', '.join(sorted(known))}"
            raise IntentError(msg)
        params = raw.get("params") or {}
        if not isinstance(params, dict):
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
                raw["expected"],
                dict(params),
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
    except IntentError as error:
        msg = f"{item.where}: device {item.device}: {error.message}"
        raise IntentError(msg) from None
    check = CHECKS.get(item.check) or module.CHECKS.get(item.check)
    if check is None:
        owners = [n for n, checks in _platform_checks().items() if item.check in checks]
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


def _reading(check: Check, item: IntentItem) -> dict[str, Any]:
    """The key of the one reading an item needs: collector and its arguments."""
    return {
        "collector": check.collector,
        "args": [item.params[name] for name in check.collect_args],
    }


def _rollup(results: list[IntentResult]) -> Verdict:
    verdicts = {result.verdict for result in results}
    return "fail" if "fail" in verdicts else "error" if "error" in verdicts else "pass"


def replay_intent(
    intent: list[IntentItem], evidence: Mapping[str, Any]
) -> IntentReport:
    """Evaluate every item from saved evidence, without devices.

    `evidence` is the content of `evidence.json` written by `run_intent`. An
    item whose device or reading is missing from it gives `error`.
    """
    devices = evidence.get("devices") if isinstance(evidence, Mapping) else None
    if not isinstance(devices, dict):
        msg = "the evidence has no devices"
        raise IntentError(msg)
    results = []
    for item in intent:
        saved = devices.get(item.device)
        if not isinstance(saved, dict) or not isinstance(saved.get("device_type"), str):
            reason = f"no evidence for device {item.device}"
            results.append((item, IntentResult(item.expected, None, "error", reason)))
            continue
        check = _resolve(item, saved["device_type"])
        key = _reading(check, item)
        readings = [
            r.get("replies")
            for r in saved.get("readings", [])
            if isinstance(r, dict) and {k: r.get(k) for k in key} == key
        ]
        if len(readings) != 1 or not isinstance(readings[0], dict):
            reason = f"expected one {key['collector']} reading of {item.device}, found {len(readings)}"
            results.append((item, IntentResult(item.expected, None, "error", reason)))
            continue
        result = check.evaluate(
            readings[0], saved["device_type"], item.params, item.expected
        )
        results.append((item, result))
    return IntentReport(_rollup([r for _, r in results]), results, dict(evidence))


def _now() -> str:
    return datetime.now(UTC).isoformat()


def run_intent(
    client: NetworkaClient,
    intent: list[IntentItem],
    save_dir: str | Path | None = None,
    source: str | Path | None = None,
    **run_options: Any,
) -> IntentReport:
    """Collect every reading once, then evaluate it exactly as `replay_intent` does.

    The device type comes from the client's inventory, and every item is
    validated before any device is read. Items that need the same collector
    with the same arguments on one device share one reading, so they see the
    same moment. With `save_dir`, the directory receives `evidence.json`,
    `results.json` and, when `source` names the intent file, a copy of it as
    `intent.yaml`. `run_options` are passed to `NetworkaClient.run`.
    """
    plan: dict[str, dict[str, Any]] = {}
    for item in intent:
        config = client.devices.get(item.device)
        if config is None or not config.device_type:
            msg = f"{item.where}: device {item.device!r} is not in the inventory"
            raise IntentError(msg)
        key = _reading(_resolve(item, config.device_type), item)
        device = plan.setdefault(
            item.device, {"device_type": config.device_type, "readings": []}
        )
        if key not in device["readings"]:
            device["readings"].append(key)
    for name, device in plan.items():
        module = platform(device["device_type"])
        device["started"] = _now()
        for reading in device["readings"]:
            collect = getattr(module, reading["collector"])
            reading["replies"] = collect(client, name, *reading["args"], **run_options)
        device["finished"] = _now()
    evidence = {"networka_version": __version__, "devices": plan}
    report = replay_intent(intent, evidence)
    if save_dir is not None:
        folder = Path(save_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / EVIDENCE_FILE).write_text(json.dumps(evidence, indent=2) + "\n")
        (folder / RESULTS_FILE).write_text(
            json.dumps(report.to_json(), indent=2) + "\n"
        )
        if source is not None:
            shutil.copyfile(source, folder / INTENT_FILE)
    return report


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
