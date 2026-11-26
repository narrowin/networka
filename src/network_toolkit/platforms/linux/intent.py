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
from network_toolkit.intent import IntentResult, Reply, Verdict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from network_toolkit.client import NetworkaClient

MEMBER_FIELDS = ("carrier", "eligible")
# Synchronization, collecting and distributing in the LACP port state.
_IN_USE = 0x38


def bonding(bond: str) -> str:
    return f"cat /proc/net/bonding/{bond}"


def collect_bond(
    client: NetworkaClient, device: str, bond: str, **run_options: Any
) -> dict[str, Reply]:
    command = bonding(bond)
    return {command: intent.read(client, device, command, run_options)}


def _one(values: list[str], what: str) -> str:
    if len(values) != 1:
        msg = f"expected one {what}, found {len(values)}"
        raise ValueError(msg)
    return values[0]


def _member(evidence: Mapping[str, Any], bond: str, member: str) -> dict[str, Any]:
    command = bonding(bond)
    text = intent.reply_output(evidence, lambda line: line.strip() == command, command)
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
    _, _, partner = section.partition("details partner lacp pdu:")
    states = re.findall(r"(?m)^\s*port state: (\d+)$", section)
    if len(states) != 2 or not partner:
        msg = f"{member} has no actor and partner port state"
        raise ValueError(msg)
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


def lacp_member(evidence: Mapping[str, Any], bond: str, member: str) -> dict:
    """Actor and partner LACP port-state bits and the partner system of one member."""
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
    wanted = {field: expected[field] for field in MEMBER_FIELDS if field in expected}
    if not wanted or set(expected) - set(MEMBER_FIELDS):
        msg = f"expected must name some of {', '.join(MEMBER_FIELDS)}"
        raise ValueError(msg)
    try:
        found = _member(evidence, bond, member)
    except ValueError as error:
        return IntentResult(wanted, None, "unavailable", str(error))
    state = {
        "carrier": found["carrier"],
        "eligible": found["aggregator"] == found["active"]
        and all(bits & _IN_USE == _IN_USE for bits in found["states"]),
    }
    observed = {field: state[field] for field in wanted}
    verdict: Verdict = "match" if observed == wanted else "mismatch"
    return IntentResult(wanted, observed, verdict)
