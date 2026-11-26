# SPDX-License-Identifier: MIT
"""Collect and normalize RouterOS evidence for the intent checks.

Every command is read as native JSON: `:serialize to=json` of the command's
`as-value` result, with `json.no-string-conversion` so that `yes` and `no`
arrive as Booleans and numbers as numbers. The collectors keep each command
with its output or error. The normalizers turn that evidence into the
neutral fields of `network_toolkit.intent`, or raise `ValueError` when it
cannot decide. `check_property` and `check_version` are RouterOS-only checks.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from network_toolkit import intent
from network_toolkit.intent import Check, IntentResult, Reply

if TYPE_CHECKING:
    from collections.abc import Mapping

    from network_toolkit.client import NetworkaClient

_JSON = ":put [:serialize to=json options=json.no-string-conversion [{}]]"
PORT_STATS = _JSON.format("/interface/bridge/port/print stats as-value")
PORT_MONITOR = _JSON.format("/interface/bridge/port/monitor {port_id} once as-value")
RESOURCE = _JSON.format("/system/resource/print as-value")
UPTIME = ":put [:serialize to=json [:tonsec [/system/resource/get uptime]]]"
# RouterOS prints LACP flags in this order, with `-` for a cleared flag.
LACP_LETTERS = "ATGSCDFE"


# The command builders accept only plain names, MAC addresses and menu paths
# and quote names, so a parameter cannot change the command.


def bridge_monitor(bridge: str) -> str:
    bridge = intent.name(bridge, "bridge")
    return _JSON.format(f'/interface/bridge/monitor "{bridge}" once as-value')


def bond_monitor(bond: str) -> str:
    bond = intent.name(bond, "bond")
    return _JSON.format(
        f'/interface/bonding/monitor-slaves bond="{bond}" once=yes as-value'
    )


def ethernet_monitor(interface: str) -> str:
    interface = intent.name(interface, "interface")
    return _JSON.format(f'/interface/ethernet/monitor "{interface}" once as-value')


def host_print(mac: str) -> str:
    return _JSON.format(
        f"/interface/bridge/host/print as-value where mac-address={intent.mac(mac)}"
    )


def bridge_print(bridge: str) -> str:
    bridge = intent.name(bridge, "bridge")
    return _JSON.format(f'/interface/bridge/print as-value where name="{bridge}"')


def menu_print(menu: str) -> str:
    """`print detail as-value` of a menu in slash form, for example `/interface/bridge/port`.

    Without `detail`, RouterOS leaves out properties that have their default value.
    """
    if not isinstance(menu, str) or not intent.MENU.fullmatch(menu):
        msg = f"menu must be a path such as /interface/bridge/port, not {menu!r}"
        raise ValueError(msg)
    return _JSON.format(f"{menu}/print detail as-value")


def collect(
    client: NetworkaClient, device: str, *commands: str, **run_options: Any
) -> dict[str, Reply]:
    """Run the commands joined with `;` as one read and keep one reply per command.

    Each command prints one JSON line, so the output is split by line. A read
    error, or a line count that differs from the command count, becomes the
    error of every reply. `run_options` are passed to `NetworkaClient.run`,
    for example `interactive_creds`.
    """
    joined = intent.read(client, device, ";".join(commands), run_options)
    lines = [line.strip() for line in (joined["output"] or "").splitlines()]
    lines = [line for line in lines if line]
    error = joined["error"]
    if error is None and len(lines) != len(commands):
        error = (
            f"the joined read returned {len(lines)} lines for {len(commands)} commands"
        )
    if error is not None:
        return {c: {"command": c, "output": None, "error": error} for c in commands}
    return {
        command: {"command": command, "output": line, "error": None}
        for command, line in zip(commands, lines, strict=True)
    }


def collect_bridge(
    client: NetworkaClient, device: str, bridge: str, **run_options: Any
) -> dict[str, Reply]:
    """Bridge monitor and port statistics: STP bridge, MLAG and bridge ports.

    They are two reads, so a failed statistics command leaves the bridge
    monitor usable.
    """
    evidence = collect(client, device, bridge_monitor(bridge), **run_options)
    evidence["stats"] = collect(client, device, PORT_STATS, **run_options)[PORT_STATS]
    return evidence


def collect_bond(
    client: NetworkaClient, device: str, bond: str, **run_options: Any
) -> dict[str, Reply]:
    return collect(client, device, bond_monitor(bond), **run_options)


def collect_host_entry(
    client: NetworkaClient, device: str, mac: str, **run_options: Any
) -> dict[str, Reply]:
    return collect(client, device, host_print(mac), **run_options)


def collect_interface(
    client: NetworkaClient, device: str, interface: str, **run_options: Any
) -> dict[str, Reply]:
    return collect(client, device, ethernet_monitor(interface), **run_options)


def collect_uptime(
    client: NetworkaClient, device: str, **run_options: Any
) -> dict[str, Reply]:
    return collect(client, device, UPTIME, **run_options)


def collect_stp_mode(
    client: NetworkaClient, device: str, bridge: str, **run_options: Any
) -> dict[str, Reply]:
    return collect(client, device, bridge_print(bridge), **run_options)


def collect_print(
    client: NetworkaClient, device: str, menu: str, **run_options: Any
) -> dict[str, Reply]:
    """`print detail as-value` of a menu, for `check_property`."""
    return collect(client, device, menu_print(menu), **run_options)


def collect_version(
    client: NetworkaClient, device: str, **run_options: Any
) -> dict[str, Reply]:
    return collect(client, device, RESOURCE, **run_options)


def _rows(evidence: Mapping[str, Any], command: str, what: str) -> list[dict]:
    """The reply saved under `command`, a JSON object or array, as a list of objects."""
    value = json.loads(intent.reply_output(evidence, command, command))
    rows = [value] if isinstance(value, dict) else value
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        msg = f"{what} must be a JSON object or an array of objects"
        raise ValueError(msg)
    return rows


def _one(values: list[Any], what: str) -> Any:
    if len(values) != 1:
        msg = f"expected one {what}, found {len(values)}"
        raise ValueError(msg)
    return values[0]


def _field(row: Mapping[str, Any], key: str, kind: type, what: str) -> Any:
    value = row.get(key)
    if not isinstance(value, kind) or (isinstance(value, bool) and kind is not bool):
        msg = f"{what} {key} is missing or is not a JSON {kind.__name__}"
        raise ValueError(msg)
    return value


def _bridge_id(value: str) -> str:
    """`0x1000.52:54:00:E1:0B:01` and `0.02:00:...` as `0xPPPP.mac` in lower case."""
    priority, _, mac = value.partition(".")
    if not re.fullmatch(r"0x[0-9a-fA-F]+|\d+", priority) or not mac:
        msg = f"bridge ID {value!r} is not priority.mac"
        raise ValueError(msg)
    return f"0x{int(priority, 0):04x}.{mac.lower()}"


def _statistics(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = json.loads(intent.reply_output(evidence, "stats", PORT_STATS))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        msg = "bridge-port statistics must be a JSON array of objects"
        raise ValueError(msg)
    return rows


def _port_id(rows: list[dict[str, Any]], bridge: str, interface: str) -> str:
    selected = [
        row
        for row in rows
        if row.get("bridge") == bridge and row.get("interface") == interface
    ]
    if len(selected) != 1:
        msg = f"expected one bridge port {bridge}/{interface}, found {len(selected)}"
        raise ValueError(msg)
    port_id = selected[0].get(".id")
    if not isinstance(port_id, str) or not re.fullmatch(r"\*[0-9A-Fa-f]+", port_id):
        msg = "selected bridge port has no valid .id"
        raise ValueError(msg)
    if sum(row.get(".id") == port_id for row in rows) != 1:
        msg = f"bridge port .id {port_id} is ambiguous"
        raise ValueError(msg)
    return port_id


def collect_bridge_port(
    client: NetworkaClient,
    device: str,
    bridge: str,
    interface: str,
    **run_options: Any,
) -> dict[str, Reply]:
    """Read the statistics and monitor replies of one bridge port.

    Read failures are kept in the evidence instead of raised. `run_options`
    are passed to `NetworkaClient.run`, for example `interactive_creds`.
    The monitor reply is absent when the port cannot be selected.
    """
    evidence = {"stats": intent.read(client, device, PORT_STATS, run_options)}
    try:
        port_id = _port_id(_statistics(evidence), bridge, interface)
    except ValueError:
        return evidence
    monitor = PORT_MONITOR.format(port_id=port_id)
    evidence["monitor"] = intent.read(client, device, monitor, run_options)
    return evidence


def bridge_port(evidence: Mapping[str, Any], bridge: str, interface: str) -> dict:
    """`forwarding`, `role` and `edge` from the evidence of `collect_bridge_port`.

    The port is selected by bridge and interface name in the statistics, and
    the monitor reply must carry the same `.id`.
    """
    port_id = _port_id(_statistics(evidence), bridge, interface)
    command = PORT_MONITOR.format(port_id=port_id)
    port = json.loads(intent.reply_output(evidence, "monitor", command))
    if not isinstance(port, dict) or port.get(".id") != port_id:
        msg = "monitor reply does not identify the selected port"
        raise ValueError(msg)
    forwarding = port.get("forwarding")
    if forwarding is None and port.get("status") == "inactive":
        # An inactive port reports only its .id, interface and status.
        forwarding = False
    if not isinstance(forwarding, bool):
        msg = "monitor forwarding is missing or is not a JSON Boolean"
        raise ValueError(msg)
    state: dict[str, Any] = {"forwarding": forwarding}
    role = port.get("role")
    if isinstance(role, str) and role:
        state["role"] = role.removesuffix("-port")
    if isinstance(port.get("edge-port"), bool):
        state["edge"] = port["edge-port"]
    return state


def bridge_ports(evidence: Mapping[str, Any], bridge: str) -> list[str]:
    """Interfaces of the bridge in the port statistics."""
    ports = []
    for row in _statistics(evidence):
        if not isinstance(row.get("bridge"), str):
            msg = "a bridge-port statistics row has no bridge"
            raise ValueError(msg)
        if row["bridge"] == bridge:
            ports.append(_field(row, "interface", str, "bridge port"))
    return ports


def _bridge(evidence: Mapping[str, Any], bridge: str) -> dict[str, Any]:
    rows = _rows(evidence, bridge_monitor(bridge), "bridge monitor")
    return _one(rows, f"{bridge} monitor")


def stp_bridge(evidence: Mapping[str, Any], bridge: str) -> dict:
    """Bridge IDs, root flag, root port and topology changes from the bridge monitor.

    Fields the monitor does not report, as with spanning tree off, are left out.
    """
    row = _bridge(evidence, bridge)
    state: dict[str, Any] = {}
    for field, key in (
        ("bridge_id", "bridge-id"),
        ("root_bridge_id", "root-bridge-id"),
    ):
        if row.get(key):
            state[field] = _bridge_id(_field(row, key, str, bridge))
    if "root-bridge" in row:
        state["root_bridge"] = _field(row, "root-bridge", bool, bridge)
    if row.get("root-port"):
        port = _field(row, "root-port", str, bridge)
        state["root_port"] = None if port == "none" else port
    if "topology-changes" in row:
        state["topology_changes"] = _field(row, "topology-changes", int, bridge)
    return state


def mlag(evidence: Mapping[str, Any], bridge: str) -> dict:
    """`mlag-state` and `mlag-active-role` from the bridge monitor, in lower case."""
    row = _bridge(evidence, bridge)
    value = _field(row, "mlag-state", str, f"the {bridge} monitor").lower()
    state = {"state": value, "connected": value == "connected"}
    if row.get("mlag-active-role"):
        state["role"] = _field(row, "mlag-active-role", str, bridge).lower()
    return state


def stp_mode(evidence: Mapping[str, Any], bridge: str) -> str:
    """`protocol-mode` of the bridge."""
    rows = _rows(evidence, bridge_print(bridge), "bridge print")
    row = _one([row for row in rows if row.get("name") == bridge], f"bridge {bridge}")
    return _field(row, "protocol-mode", str, f"bridge {bridge}")


def lacp_member(evidence: Mapping[str, Any], bond: str, member: str) -> dict:
    """Actor and partner LACP flags and the partner system of one bond member.

    RouterOS marks a member that has an LACP partner with `partner: true`.
    Without a partner, `partner` and `partner_system` are left out and only
    the actor flags are returned. The partner MAC is lower-cased.
    """
    rows = _rows(evidence, bond_monitor(bond), f"{bond} monitor")
    row = _one([r for r in rows if r.get("port") == member], f"{bond} member {member}")
    partner = row.get("partner", False)
    if not isinstance(partner, bool):
        msg = f"{member} partner is not a JSON Boolean"
        raise ValueError(msg)
    sides = (
        (("actor", "flags"), ("partner", "partner-flags"))
        if partner
        else (("actor", "flags"),)
    )
    state: dict[str, Any] = {}
    for side, key in sides:
        flags = _field(row, key, str, member)
        if len(flags) != len(LACP_LETTERS) or any(
            flag not in (letter, "-")
            for flag, letter in zip(flags, LACP_LETTERS, strict=True)
        ):
            msg = f"{member} {key} {flags!r} is not in {LACP_LETTERS} form"
            raise ValueError(msg)
        state[side] = {
            name: flag != "-"
            for name, flag in zip(intent.LACP_FLAGS, flags, strict=True)
        }
    if partner:
        state["partner_system"] = {
            "priority": _field(row, "partner-sys-priority", int, member),
            "mac": _field(row, "partner-sys-id", str, member).lower(),
        }
    return state


def host_entry(evidence: Mapping[str, Any], bridge: str, mac: str) -> str | None:
    """`on-interface` of the host entry for `mac` on `bridge`, `None` without one.

    An entry for the MAC on another bridge, or a row without `mac-address`,
    `bridge` or `on-interface`, cannot decide and raises.
    """
    ports = set()
    for row in _rows(evidence, host_print(mac), "bridge host print"):
        found = _field(row, "mac-address", str, "host entry")
        on = _field(row, "bridge", str, f"host entry {found}")
        if found.lower() != mac.lower():
            continue
        if on != bridge:
            msg = f"the host entry for {mac} is on bridge {on}, not {bridge}"
            raise ValueError(msg)
        ports.add(_field(row, "on-interface", str, mac))
    if len(ports) > 1:
        msg = f"host entries for {mac} on {bridge} disagree: {sorted(ports)}"
        raise ValueError(msg)
    return ports.pop() if ports else None


def interface_up(evidence: Mapping[str, Any], interface: str) -> bool:
    """`status` of the Ethernet monitor: `link-ok` is up, `no-link` is down."""
    rows = _rows(evidence, ethernet_monitor(interface), "Ethernet monitor")
    row = _one(rows, f"monitor of {interface}")
    if row.get("name", interface) != interface:
        msg = f"the monitor reply is for {row.get('name')!r}, not {interface}"
        raise ValueError(msg)
    status = _field(row, "status", str, interface)
    if status not in ("link-ok", "no-link"):
        msg = f"{interface} status is {status!r}"
        raise ValueError(msg)
    return status == "link-ok"


def uptime_ns(evidence: Mapping[str, Any]) -> int:
    """Uptime in nanoseconds from the `UPTIME` command."""
    value = json.loads(intent.reply_output(evidence, UPTIME, UPTIME))
    if not isinstance(value, int) or isinstance(value, bool):
        msg = "uptime is not a JSON number"
        raise ValueError(msg)
    return value


def check_property(
    evidence: Mapping[str, Any],
    menu: str,
    where: Mapping[str, Any],
    name: str,
    expected: Any,
) -> IntentResult:
    """Compare one property of a menu entry; an absent property is `error`.

    `menu` is the path in slash form, for example `/interface/bridge/port`,
    as read by `collect_print`. `where` selects one entry by its JSON values,
    for example `{"interface": "ether4"}`. Values compare
    exactly as RouterOS returns them: for example `edge` is the string
    `"yes"` or `"auto"`, `bpdu-guard` a Boolean, `pvid` a number, and
    `vlan-ids` an array of strings.
    """

    def observe() -> Any:
        rows = _rows(evidence, menu_print(menu), f"{menu} print")
        found = " ".join(f"{key}={value}" for key, value in where.items())
        selected = [
            r
            for r in rows
            if all(k in r and intent.same(v, r[k]) for k, v in where.items())
        ]
        row = _one(selected, f"entry with {found}")
        if name not in row:
            msg = f"the entry with {found} has no property {name}"
            raise ValueError(msg)
        return row[name]

    return intent.compare(expected, observe)


def check_version(evidence: Mapping[str, Any], expected: str) -> IntentResult:
    """Compare the `version` of the system resource, without the channel."""

    def observe() -> str:
        row = _one(_rows(evidence, RESOURCE, "system resource"), "system resource")
        words = _field(row, "version", str, "system resource").split()
        if not words:
            msg = "system resource version is empty"
            raise ValueError(msg)
        return words[0]

    return intent.compare(expected, observe)


# RouterOS-only checks an intent file can name.
CHECKS = {
    "property": Check(
        ("menu", "where", "name"),
        "collect_print",
        ("menu",),
        lambda ev, _dt, p, e: check_property(ev, p["menu"], p["where"], p["name"], e),
    ),
    "version": Check(
        (), "collect_version", (), lambda ev, _dt, _p, e: check_version(ev, e)
    ),
}
