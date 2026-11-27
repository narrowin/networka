# SPDX-License-Identifier: MIT
"""Read and normalize Linux bonding evidence for the intent checks.

The evidence is the iproute2 JSON of the bond and its members from the
Linux bonding driver, which Cumulus Linux also uses. `check_bond_member` is
a Linux-only check of the driver's own view of a member.
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
_MII = {"UP": True, "DOWN": False}


def _bond_name(bond: str) -> str:
    bond = intent.name(bond, "bond")
    if "/" in bond:
        msg = f"bond must be an interface name without '/', not {bond!r}"
        raise ValueError(msg)
    return bond


def bond_link(bond: str) -> str:
    """The read of the bond itself; `bond` must be a plain interface name."""
    return f"ip -j -d link show dev {_bond_name(bond)}"


def bond_slaves(bond: str) -> str:
    """The read of every member of the bond, with its bonding details."""
    return f"ip -j -d link show master {_bond_name(bond)}"


def read_bond(
    client: NetworkaClient,
    device: str,
    bond: str,
    member: str | None = None,
    **run_options: Any,
) -> dict[str, Reply]:
    """The bond and all its members; the member read lists every member."""
    return {
        command: intent.read(client, device, command, run_options)
        for command in (bond_link(bond), bond_slaves(bond))
    }


def _one(values: list[Any], what: str) -> Any:
    if len(values) != 1:
        msg = f"expected one {what}, found {len(values)}"
        raise ValueError(msg)
    return values[0]


def _rows(evidence: Mapping[str, Any], command: str) -> list[dict]:
    rows = intent.load_json(intent.reply_output(evidence, command))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        msg = f"the reply to {command} is not a JSON array of objects"
        raise ValueError(msg)
    return rows


def _int(data: Mapping[str, Any], key: str, what: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"{what} {key} is missing or is not a JSON number"
        raise ValueError(msg)
    return value


def _bond(evidence: Mapping[str, Any], bond: str) -> dict[str, Any]:
    """The `info_data` of the bond's own row, which must name the bond."""
    row = _one(_rows(evidence, bond_link(bond)), f"link row for {bond}")
    linkinfo = row.get("linkinfo")
    if row.get("ifname") != bond:
        msg = f"the link row names {row.get('ifname')!r}, not {bond}"
        raise ValueError(msg)
    if not isinstance(linkinfo, dict) or linkinfo.get("info_kind") != "bond":
        msg = f"{bond} is not a bond"
        raise ValueError(msg)
    data = linkinfo.get("info_data")
    if not isinstance(data, dict) or not isinstance(data.get("mode"), str):
        msg = f"{bond} has no bond mode"
        raise ValueError(msg)
    return data


def _slaves(evidence: Mapping[str, Any], bond: str) -> list[dict]:
    """The member rows; each must name itself and the bond as its master."""
    rows = _rows(evidence, bond_slaves(bond))
    for row in rows:
        if not isinstance(row.get("ifname"), str) or row.get("master") != bond:
            msg = f"a member row does not name its port and master {bond}"
            raise ValueError(msg)
    return rows


def _member(evidence: Mapping[str, Any], bond: str, member: str) -> dict[str, Any]:
    data = _bond(evidence, bond)
    if data["mode"] != "802.3ad":
        msg = f"{bond} is not an 802.3ad (LACP) bond"
        raise ValueError(msg)
    rows = [r for r in _slaves(evidence, bond) if r["ifname"] == member]
    row = _one(rows, f"member row for {member}")
    linkinfo = row.get("linkinfo")
    slave = linkinfo.get("info_slave_data") if isinstance(linkinfo, dict) else None
    if not isinstance(slave, dict):
        msg = f"{member} has no bonding details"
        raise ValueError(msg)
    mii = slave.get("mii_status")
    if mii not in _MII:
        msg = f"{member} mii_status is {mii!r}, not UP or DOWN"
        raise ValueError(msg)
    states = [
        _int(slave, f"ad_{side}_oper_port_state", member)
        for side in ("actor", "partner")
    ]
    if any(not 0 <= state <= 255 for state in states):
        msg = f"{member} port state is not a byte: {states}"
        raise ValueError(msg)
    info = data.get("ad_info")
    return {
        "states": states,
        "carrier": _MII[mii],
        "aggregator": _int(slave, "ad_aggregator_id", member),
        "active": info if isinstance(info, dict) else None,
    }


def bond_members(evidence: Mapping[str, Any], bond: str) -> list[str]:
    """The `ifname` of every member row; the bond's own row proves it exists."""
    _bond(evidence, bond)
    return [row["ifname"] for row in _slaves(evidence, bond)]


def lacp_member(evidence: Mapping[str, Any], bond: str, member: str) -> dict:
    """Actor and partner LACP port-state bits and the partner system of one member.

    The bits are the numeric `ad_actor_oper_port_state` and
    `ad_partner_oper_port_state`, which older iproute2 also prints. The JSON
    has no partner system priority and only the partner MAC of the active
    aggregator, so `partner_system` holds only `mac`, and only for a member
    in the active aggregator.
    """
    found = _member(evidence, bond, member)
    sides = dict(zip(("actor", "partner"), found["states"], strict=True))
    state: dict[str, Any] = {
        side: {
            name: bool(bits >> index & 1)
            for index, name in enumerate(intent.LACP_FLAGS)
        }
        for side, bits in sides.items()
    }
    active = found["active"]
    state["partner_system"] = {}
    if active is not None and found["aggregator"] == _int(
        active, "aggregator", f"{bond} ad_info"
    ):
        mac = active.get("partner_mac")
        if not isinstance(mac, str):
            msg = f"{bond} ad_info has no partner_mac"
            raise ValueError(msg)
        state["partner_system"]["mac"] = mac.lower()
    return state


def check_bond_member(
    evidence: Mapping[str, Any],
    bond: str,
    member: str,
    expected: Mapping[str, bool],
) -> IntentResult:
    """Compare the bonding driver's `carrier` (`mii_status`) and `eligible` of a member.

    `eligible` means the member is in the active aggregator and both its actor
    and partner port state are synchronized, collecting and distributing.
    """
    intent.expect(CHECKS["bond_member"].expected, expected, "bond_member")

    def observe() -> dict[str, bool]:
        found = _member(evidence, bond, member)
        active = found["active"]
        if active is None and "eligible" in expected:
            msg = f"{bond} has no active aggregator"
            raise ValueError(msg)
        state = {"carrier": found["carrier"]}
        if active is not None:
            state["eligible"] = found["aggregator"] == _int(
                active, "aggregator", f"{bond} ad_info"
            ) and all(bits & _IN_USE == _IN_USE for bits in found["states"])
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
    parts = ["ping", "-n", "-c", str(intent.ping_count(count)), "-W", "1"]
    for value, what in ((interface, "interface"), (vrf, "vrf")):
        if value is not None:
            device = intent.name(value, what)
            if "/" in device:
                msg = f"{what} must be a name without '/', not {device!r}"
                raise ValueError(msg)
            parts += ["-I", device]
    return " ".join([*parts, intent.address(dest)])


def read_ping(
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
    the `count` pings is answered. A "Destination Host Unreachable" reply
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
        msg = f"the ping sent {sent} pings, not {count}"
        raise ValueError(msg)
    return {
        "sent": int(sent),
        "received": int(received),
        "reachable": int(received) == int(sent),
    }


# Param combinations Linux cannot run, keyed by check name. `intent._resolve`
# calls each rule with the item's params before any device is read.
PARAM_RULES = {"ping": _ping_device}

# Linux-only checks an intent file can name.
CHECKS = {
    "bond_member": Check(
        ("bond", "member"),
        "read_bond",
        lambda ev, _dt, p, e: check_bond_member(ev, p["bond"], p["member"], e),
        expected={"carrier": (bool,), "eligible": (bool,)},
    ),
}
intent.claim("linux", CHECKS)
