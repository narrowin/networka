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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
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
