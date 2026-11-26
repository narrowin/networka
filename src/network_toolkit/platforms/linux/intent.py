# SPDX-License-Identifier: MIT
"""Collect and normalize Linux bonding evidence for the intent checks.

The evidence is the text of `/proc/net/bonding/<bond>` from the Linux
bonding driver, which Cumulus Linux also uses. `check_bond_member` is a
Linux-only check of the driver's own view of a member.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from network_toolkit import intent
from network_toolkit.intent import Check, IntentResult, Reply

if TYPE_CHECKING:
    from collections.abc import Mapping

    from network_toolkit.client import NetworkaClient

MEMBER_FIELDS = ("carrier", "eligible")
# Synchronization, collecting and distributing in the LACP port state.
_IN_USE = 0x38


def bonding(bond: str) -> str:
    """The read of one bond; `bond` must be a plain interface name."""
    bond = intent.name(bond, "bond")
    if "/" in bond:
        msg = f"bond must be an interface name without '/', not {bond!r}"
        raise ValueError(msg)
    return f"cat /proc/net/bonding/{bond}"


def collect_bond(
    client: NetworkaClient,
    device: str,
    bond: str,
    member: str | None = None,
    **run_options: Any,
) -> dict[str, Reply]:
    """`/proc/net/bonding/<bond>`; it lists every member, so `member` is not needed."""
    command = bonding(bond)
    return {command: intent.read(client, device, command, run_options)}


def _one(values: list[Any], what: str) -> Any:
    if len(values) != 1:
        msg = f"expected one {what}, found {len(values)}"
        raise ValueError(msg)
    return values[0]


def _member(evidence: Mapping[str, Any], bond: str, member: str) -> dict[str, Any]:
    command = bonding(bond)
    text = intent.reply_output(evidence, command)
    section = _one(
        re.findall(
            rf"(?m)^Slave Interface: {re.escape(member)}\n([\s\S]*?)(?=^Slave Interface: |\Z)",
            text,
        ),
        f"section for {member}",
    )
    active = _one(
        re.findall(r"(?m)^Active Aggregator Info:\n\s*Aggregator ID: (\d+)$", text),
        "active aggregator",
    )
    blocks = {
        side: _one(
            re.findall(
                rf"(?m)^details {side} lacp pdu:\n((?:[ \t]+\S.*\n?)*)", section
            ),
            f"{side} lacp pdu block of {member}",
        )
        for side in ("actor", "partner")
    }
    states = [
        _one(re.findall(r"(?m)^\s*port state: (\d+)$", block), f"{side} port state")
        for side, block in blocks.items()
    ]
    if any(int(state) > 255 for state in states):
        msg = f"{member} port state is not a byte: {states}"
        raise ValueError(msg)
    partner = blocks["partner"]
    mii = _one(re.findall(r"(?m)^MII Status: (up|down)$", section), "MII Status")
    return {
        "states": [int(state) for state in states],
        "carrier": mii == "up",
        "aggregator": _one(
            re.findall(r"(?m)^Aggregator ID: (\d+)$", section), "Aggregator ID"
        ),
        "active": active,
        "partner": partner,
    }


def bond_members(evidence: Mapping[str, Any], bond: str) -> list[str]:
    """The `Slave Interface:` names of `/proc/net/bonding/<bond>`.

    A successful read of the file proves the bond exists.
    """
    text = intent.reply_output(evidence, bonding(bond))
    if (
        not text.startswith("Ethernet Channel Bonding Driver:")
        and "Bonding Mode:" not in text
    ):
        msg = f"the reply for {bond} is not a bonding status file"
        raise ValueError(msg)
    return re.findall(r"(?m)^Slave Interface: (\S+)$", text)


def lacp_member(evidence: Mapping[str, Any], bond: str, member: str) -> dict:
    """Actor and partner LACP port-state bits and the partner system of one member.

    Each side is read from its own labelled block, `details actor lacp pdu`
    and `details partner lacp pdu`; a missing block raises.
    """
    found = _member(evidence, bond, member)
    partner = found["partner"]
    priority = _one(
        re.findall(r"(?m)^\s*system priority: (\d+)$", partner),
        "partner system priority",
    )
    mac = _one(
        re.findall(r"(?m)^\s*system mac address: (\S+)$", partner), "partner system MAC"
    )
    sides = dict(zip(("actor", "partner"), found["states"], strict=True))
    state: dict[str, Any] = {
        side: {
            name: bool(bits >> index & 1)
            for index, name in enumerate(intent.LACP_FLAGS)
        }
        for side, bits in sides.items()
    }
    state["partner_system"] = {
        "priority": int(priority),
        "mac": mac.lower(),
    }
    return state


def check_bond_member(
    evidence: Mapping[str, Any],
    bond: str,
    member: str,
    expected: Mapping[str, bool],
) -> IntentResult:
    """Compare the bonding driver's `carrier` (MII Status) and `eligible` of a member.

    `eligible` means the member is in the active aggregator and both its actor
    and partner port state are synchronized, collecting and distributing.
    """
    intent.expect(CHECKS["bond_member"].expected, expected, "bond_member")

    def observe() -> dict[str, bool]:
        found = _member(evidence, bond, member)
        state = {
            "carrier": found["carrier"],
            "eligible": found["aggregator"] == found["active"]
            and all(bits & _IN_USE == _IN_USE for bits in found["states"]),
        }
        return {name: state[name] for name in expected}

    return intent.compare(dict(expected), observe)


def _ping_device(params: Mapping[str, Any]) -> None:
    """iputils binds to one device: an interface or a VRF, not both."""
    if params.get("interface") is not None and params.get("vrf") is not None:
        msg = "ping takes interface or vrf on Linux, not both"
        raise ValueError(msg)


def ping_command(
    dest: str, count: int, interface: str | None = None, vrf: str | None = None
) -> str:
    """`ping -n -c <count> -W 1 [-I <interface or vrf>] <dest>`, validated.

    iputils binds to a VRF through its device, so a VRF is given with `-I`.
    """
    _ping_device({"interface": interface, "vrf": vrf})
    parts = ["ping", "-n", "-c", str(intent.probes(count)), "-W", "1"]
    for value, what in ((interface, "interface"), (vrf, "vrf")):
        if value is not None:
            device = intent.name(value, what)
            if "/" in device:
                msg = f"{what} must be a name without '/', not {device!r}"
                raise ValueError(msg)
            parts += ["-I", device]
    return " ".join([*parts, intent.address(dest)])


def collect_ping(
    client: NetworkaClient,
    device: str,
    dest: str,
    count: int,
    interface: str | None = None,
    vrf: str | None = None,
    **run_options: Any,
) -> dict[str, Reply]:
    """Ping `dest` from the device. Ping has no JSON output, so this is text."""
    command = ping_command(dest, count, interface, vrf)
    return {command: intent.read(client, device, command, run_options)}


def ping(
    evidence: Mapping[str, Any],
    dest: str,
    count: int,
    interface: str | None = None,
    vrf: str | None = None,
) -> dict[str, Any]:
    """`sent`, `received` and `reachable` from the iputils summary line.

    The `PING <dest>` header and the `--- <dest> ping statistics ---` line
    identify the reply, the header names the interface or VRF device when
    one was given, and the number sent must be `count`. A reply that is only
    `ping: connect: Network is unreachable` means no route to `dest`: none of
    the `count` probes is answered. A "Destination Host Unreachable" reply
    carries the statistics line and is read from it.
    """
    text = intent.reply_output(evidence, ping_command(dest, count, interface, vrf))
    interface = interface if interface is not None else vrf
    if text.strip() == "ping: connect: Network is unreachable":
        return {"sent": count, "received": 0, "reachable": False}
    header = _one(
        re.findall(rf"(?m)^PING {re.escape(dest)} \(.*$", text), f"PING {dest} header"
    )
    _one(
        re.findall(rf"(?m)^--- {re.escape(dest)} ping statistics ---$", text),
        f"{dest} ping statistics",
    )
    if interface is not None and f" {interface}:" not in header:
        msg = f"the ping header does not name interface {interface}: {header}"
        raise ValueError(msg)
    sent, received = _one(
        re.findall(r"(?m)^(\d+) packets transmitted, (\d+) received", text),
        "ping summary line",
    )
    if int(sent) != count:
        msg = f"the ping sent {sent} probes, not {count}"
        raise ValueError(msg)
    return {
        "sent": int(sent),
        "received": int(received),
        "reachable": int(received) == int(sent),
    }


# Linux-only checks an intent file can name.
# Param combinations Linux cannot run, checked before any device is read.
PARAM_RULES = {"ping": _ping_device}

CHECKS = {
    "bond_member": Check(
        ("bond", "member"),
        "collect_bond",
        lambda ev, _dt, p, e: check_bond_member(ev, p["bond"], p["member"], e),
        expected={"carrier": (bool,), "eligible": (bool,)},
    ),
}
