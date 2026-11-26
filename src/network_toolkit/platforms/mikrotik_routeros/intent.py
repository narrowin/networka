# SPDX-License-Identifier: MIT
"""Collect and normalize RouterOS evidence for the intent checks.

The collectors read through a `NetworkaClient` and keep each command with its
output or error. The normalizers turn saved evidence into the neutral fields
of `network_toolkit.intent`, or raise `ValueError` when it cannot decide.
`check_property` and `check_version` are RouterOS-only checks.

The bridge-port reply of `collect_bridge_port` is native JSON. The other
normalizers read the CLI text of the commands built here. One reply may hold
several of these commands joined with `;`, as RouterOS runs them in one read.
Each value a normalizer needs must then appear once in the joined output.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from network_toolkit import intent
from network_toolkit.intent import IntentResult, Reply, Verdict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from network_toolkit.client import NetworkaClient

_JSON = ":put [:serialize to=json options=json.no-string-conversion [{}]]"
PORT_STATS = _JSON.format("/interface/bridge/port/print stats as-value")
PORT_MONITOR = _JSON.format("/interface/bridge/port/monitor {port_id} once as-value")
UPTIME = ':put ("uptime-ns=" . [:tonsec [/system resource get uptime]])'
RESOURCE = "/system resource print"
BRIDGES = "/interface bridge print detail without-paging"
# RouterOS prints LACP flags in this order, with `-` for a cleared flag.
LACP_LETTERS = "ATGSCDFE"


def ethernet_monitor(interface: str) -> str:
    return f"/interface ethernet monitor {interface} once"


def bridge_monitor(bridge: str) -> str:
    return f"/interface bridge monitor {bridge} once"


def port_monitor(bridge: str) -> str:
    return f"/interface bridge port monitor [find where bridge={bridge}] once"


def host_print(mac: str) -> str:
    return f"/interface bridge host print detail without-paging where mac-address={mac}"


def bond_monitor(bond: str) -> str:
    return f"/interface bonding monitor-slaves bond={bond} once=yes"


def bridge_print(bridge: str) -> str:
    return f"{BRIDGES} where name={bridge}"


def collect(
    client: NetworkaClient, device: str, *commands: str, **run_options: Any
) -> dict[str, Reply]:
    """Run the commands joined with `;` as one read, keyed by that line.

    `run_options` are passed to `NetworkaClient.run`, for example
    `interactive_creds`. A read failure is kept in the evidence, not raised.
    """
    line = ";".join(commands)
    return {line: intent.read(client, device, line, run_options)}


def collect_bridge(
    client: NetworkaClient, device: str, bridge: str, **run_options: Any
) -> dict[str, Reply]:
    """Bridge and port monitor: STP bridge, MLAG, bridge ports and port state."""
    return collect(
        client, device, bridge_monitor(bridge), port_monitor(bridge), **run_options
    )


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


def _canonical(command: str) -> str:
    """`/interface/bridge/monitor` and `/interface bridge monitor` are one command."""
    head, _, rest = command.strip().partition(" ")
    if head.startswith("/"):
        head = "/" + " ".join(head[1:].split("/"))
    return " ".join(f"{head} {rest}".split())


def _text(evidence: Mapping[str, Any], *commands: str) -> str:
    wanted = {_canonical(command) for command in commands}

    def accepts(line: str) -> bool:
        return any(_canonical(part) in wanted for part in line.split(";"))

    return intent.reply_output(evidence, accepts, commands[0])


def _one(values: list[Any], what: str) -> Any:
    if len(values) != 1:
        msg = f"expected one {what}, found {len(values)}"
        raise ValueError(msg)
    return values[0]


def _vertical(text: str, key: str) -> str | None:
    """The value of a `key: value` line, `None` when the key is absent."""
    values = re.findall(rf"^[ \t]*{re.escape(key)}:[ \t]*(.*?)[ \t]*$", text, re.M)
    return _one(values, f"{key} line") if values else None


def _yes_no(value: str, what: str) -> bool:
    if value not in ("yes", "no"):
        msg = f"{what} is {value!r}, not yes or no"
        raise ValueError(msg)
    return value == "yes"


def _bridge_id(value: str) -> str:
    """`0x1000.52:54:00:E1:0B:01` and `0.02:00:...` as `0xPPPP.mac` in lower case."""
    priority, _, mac = value.partition(".")
    if not re.fullmatch(r"0x[0-9a-fA-F]+|\d+", priority) or not mac:
        msg = f"bridge ID {value!r} is not priority.mac"
        raise ValueError(msg)
    return f"0x{int(priority, 0):04x}.{mac.lower()}"


def _tokens(text: str) -> list[tuple[str, str]]:
    pairs = re.findall(r'(?<![\w"=-])([a-z][\w.-]*)=("[^"]*"|\S*)', text)
    return [(key, value.strip('"')) for key, value in pairs]


def _spans(text: str, key: str, value: str) -> list[str]:
    """Entries that start at `key=value`, up to the next `key=` or `Flags:` header."""
    starts = [m.start() for m in re.finditer(rf"(?<![\w-]){re.escape(key)}=", text)]
    spans = []
    for start, end in zip(starts, [*starts[1:], len(text)], strict=True):
        span = text[start:end]
        if header := re.search(r"^Flags:", span, re.M):
            span = span[: header.start()]
        if _tokens(span)[0][1].lower() == value.lower():
            spans.append(span)
    return spans


def _fields(span: str, keys: tuple[str, ...], what: str) -> dict[str, str]:
    tokens = _tokens(span)
    return {
        key: _one([v for k, v in tokens if k == key], f"{key} for {what}")
        for key in keys
    }


def _table(text: str) -> tuple[dict[str, dict[str, str]], int, int]:
    """The port monitor table, one dict per port, and where it starts and ends.

    Cells are read by the column of the port name, so a blank cell is left
    out instead of shifting the values that follow it.
    """
    heads = list(re.finditer(r"^([ \t]*interface:)(.*)$", text, re.M))
    head = _one(heads, "bridge port monitor table")
    colon = len(head[1])
    cells = [(m.start() + colon, m[0]) for m in re.finditer(r"\S+", head[2])]
    table: dict[str, dict[str, str]] = {name: {} for _, name in cells}
    if len(table) != len(cells):
        msg = "the port monitor names a port twice"
        raise ValueError(msg)
    end = head.end()
    for line in re.finditer(r"\n([^\n]*)", text[head.end() :]):
        row = re.match(r"^[ \t]*([\w-]+):", line[1])
        if row is None or row.end() != colon:
            break
        end = head.end() + line.end()
        for index, (start, name) in enumerate(cells):
            stop = cells[index + 1][0] if index + 1 < len(cells) else len(line[1])
            if value := line[1][start:stop].strip():
                table[name][row[1]] = value
    return table, head.start(), end


def _port_table(text: str) -> dict[str, dict[str, str]]:
    return _table(text)[0]


def _outside_table(text: str) -> str:
    """The text without the port monitor table, whose rows reuse bridge monitor keys."""
    if not re.search(r"^[ \t]*interface:", text, re.M):
        return text
    _, start, end = _table(text)
    return text[:start] + text[end:]


def _entry(text: str, where: Mapping[str, str], name: str) -> str | None:
    """Property `name` of the one `print detail` entry whose properties match `where`."""
    starts = [m.start() for m in re.finditer(r"^[ \t]*\d+[ \t]", text, re.M)]
    entries = [
        dict(reversed(_tokens(text[start:end])))
        for start, end in zip(starts, [*starts[1:], len(text)], strict=True)
    ]
    selected = [
        entry for entry in entries if all(entry.get(k) == v for k, v in where.items())
    ]
    found = " ".join(f"{key}={value}" for key, value in where.items())
    return _one(selected, f"entry with {found}").get(name)


def _output(evidence: Mapping[str, Any], key: str, command: str) -> str:
    reply = evidence.get(key)
    if not isinstance(reply, dict):
        msg = f"no {key} reply in the evidence"
        raise ValueError(msg)
    if reply.get("error"):
        raise ValueError(str(reply["error"]))
    if reply.get("command") != command:
        msg = f"{key} reply is for a different command"
        raise ValueError(msg)
    output = reply.get("output")
    if not isinstance(output, str):
        msg = f"{key} reply has no output"
        raise ValueError(msg)
    return output


def _port_id(stats: str, bridge: str, interface: str) -> str:
    rows = json.loads(stats)
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        msg = "bridge-port statistics must be a JSON array of objects"
        raise ValueError(msg)
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
    """Read the native JSON statistics and monitor replies of one bridge port.

    Read failures are kept in the evidence instead of raised. `run_options`
    are passed to `NetworkaClient.run`, for example `interactive_creds`.
    The monitor reply is absent when the port cannot be selected.
    """
    evidence = {"stats": intent.read(client, device, PORT_STATS, run_options)}
    try:
        port_id = _port_id(_output(evidence, "stats", PORT_STATS), bridge, interface)
    except ValueError:
        return evidence
    monitor = PORT_MONITOR.format(port_id=port_id)
    evidence["monitor"] = intent.read(client, device, monitor, run_options)
    return evidence


def _role(value: Any) -> str | None:
    return value.removesuffix("-port") if isinstance(value, str) and value else None


def _json_port(evidence: Mapping[str, Any], bridge: str, interface: str) -> dict:
    port_id = _port_id(_output(evidence, "stats", PORT_STATS), bridge, interface)
    command = PORT_MONITOR.format(port_id=port_id)
    port = json.loads(_output(evidence, "monitor", command))
    if not isinstance(port, dict) or port.get(".id") != port_id:
        msg = "monitor reply does not identify the selected port"
        raise ValueError(msg)
    forwarding = port.get("forwarding")
    if not isinstance(forwarding, bool):
        msg = "monitor forwarding is missing or is not a JSON Boolean"
        raise ValueError(msg)
    state: dict[str, Any] = {"forwarding": forwarding}
    if role := _role(port.get("role")):
        state["role"] = role
    if isinstance(port.get("edge-port"), bool):
        state["edge"] = port["edge-port"]
    return state


def bridge_port(evidence: Mapping[str, Any], bridge: str, interface: str) -> dict:
    """Neutral port state from `collect_bridge_port` JSON or the port monitor text.

    Evidence with a `stats` reply is read as JSON. Otherwise the text of
    `port_monitor(bridge)` is read.
    """
    if "stats" in evidence:
        return _json_port(evidence, bridge, interface)
    try:
        text = _text(evidence, port_monitor(bridge))
    except ValueError:
        return _json_port(evidence, bridge, interface)
    row = _port_table(text).get(interface)
    if row is None:
        msg = f"no bridge port {bridge}/{interface} in the port monitor"
        raise ValueError(msg)
    what = f"{bridge}/{interface}"
    state: dict[str, Any] = {}
    if "forwarding" in row:
        state["forwarding"] = _yes_no(row["forwarding"], f"{what} forwarding")
    if role := _role(row.get("role")):
        state["role"] = role
    if "edge-port" in row:
        state["edge"] = _yes_no(row["edge-port"], f"{what} edge-port")
    return state


def bridge_ports(evidence: Mapping[str, Any], bridge: str) -> list[str]:
    """The interfaces of the port monitor table."""
    return list(_port_table(_text(evidence, port_monitor(bridge))))


def stp_bridge(evidence: Mapping[str, Any], bridge: str) -> dict:
    """Bridge IDs, root flag, root port and topology changes from the bridge monitor.

    Fields the monitor does not print, as with spanning tree off, are left out.
    """
    text = _outside_table(_text(evidence, bridge_monitor(bridge)))
    state: dict[str, Any] = {}
    for field, key in (
        ("bridge_id", "bridge-id"),
        ("root_bridge_id", "root-bridge-id"),
    ):
        if value := _vertical(text, key):
            state[field] = _bridge_id(value)
    if value := _vertical(text, "root-bridge"):
        state["root_bridge"] = _yes_no(value, "root-bridge")
    if value := _vertical(text, "root-port"):
        state["root_port"] = None if value == "none" else value
    if value := _vertical(text, "topology-changes"):
        if not value.isdigit():
            msg = f"topology-changes is {value!r}"
            raise ValueError(msg)
        state["topology_changes"] = int(value)
    return state


def stp_mode(evidence: Mapping[str, Any], bridge: str) -> str:
    """`protocol-mode` of the bridge from a bridge print, with or without `where`."""
    text = _text(evidence, bridge_print(bridge), BRIDGES)
    mode = _entry(text, {"name": bridge}, "protocol-mode")
    if not mode:
        msg = f"bridge {bridge} has no protocol-mode"
        raise ValueError(msg)
    return mode


def mlag(evidence: Mapping[str, Any], bridge: str) -> dict:
    """`mlag-state` and `mlag-active-role` from the bridge monitor, in lower case."""
    text = _outside_table(_text(evidence, bridge_monitor(bridge)))
    value = _vertical(text, "mlag-state")
    if not value:
        msg = f"the {bridge} monitor has no mlag-state"
        raise ValueError(msg)
    state = {"state": value.lower(), "connected": value.lower() == "connected"}
    if role := _vertical(text, "mlag-active-role"):
        state["role"] = role.lower()
    return state


def lacp_member(evidence: Mapping[str, Any], bond: str, member: str) -> dict:
    """Actor and partner LACP flags and the partner system of one bond member."""
    text = _text(evidence, bond_monitor(bond))
    span = _one(_spans(text, "port", member), f"port={member} entry")
    keys = ("flags", "partner-flags", "partner-sys-id", "partner-sys-priority")
    fields = _fields(span, keys, member)
    state: dict[str, Any] = {}
    for side, key in (("actor", "flags"), ("partner", "partner-flags")):
        flags = fields[key]
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
    if not fields["partner-sys-priority"].isdigit():
        msg = f"{member} partner-sys-priority is not a number"
        raise ValueError(msg)
    state["partner_system"] = {
        "priority": int(fields["partner-sys-priority"]),
        "mac": fields["partner-sys-id"].lower(),
    }
    return state


def host_interface(evidence: Mapping[str, Any], bridge: str, mac: str) -> str | None:
    """`on-interface` of the host entry for `mac` on `bridge`, `None` without one.

    Identical entries, as from the same print twice in one read, count once.
    """
    text = _text(evidence, host_print(mac))
    entries = [
        _fields(span, ("bridge", "on-interface"), mac)
        for span in _spans(text, "mac-address", mac)
    ]
    ports = {entry["on-interface"] for entry in entries if entry["bridge"] == bridge}
    if len(ports) > 1:
        msg = f"host entries for {mac} on {bridge} disagree: {sorted(ports)}"
        raise ValueError(msg)
    return ports.pop() if ports else None


def interface_up(evidence: Mapping[str, Any], interface: str) -> bool:
    """`status` of the Ethernet monitor: `link-ok` is up, `no-link` is down."""
    text = _text(evidence, ethernet_monitor(interface))
    statuses = re.findall(
        rf"^[ \t]*name:[ \t]*{re.escape(interface)}[ \t]*\n[ \t]*status:[ \t]*(\S+)",
        text,
        re.M,
    )
    status = _one(statuses, f"status of {interface}")
    if status not in ("link-ok", "no-link"):
        msg = f"{interface} status is {status!r}"
        raise ValueError(msg)
    return status == "link-ok"


def uptime_ns(evidence: Mapping[str, Any]) -> int:
    """Uptime in nanoseconds from the `UPTIME` command."""
    text = _text(evidence, UPTIME)
    return int(_one(re.findall(r"^uptime-ns=(\d+)\b", text, re.M), "uptime-ns line"))


def check_bridge_port_forwarding(
    evidence: Mapping[str, Any], bridge: str, interface: str, expected: bool = True
) -> IntentResult:
    """Compare the forwarding Boolean of one bridge port.

    The port is selected by bridge and interface name in the statistics, and
    the monitor reply must carry the same `.id`. A read error, invalid JSON,
    an ambiguous port, or a missing field gives `unavailable`.
    """
    return intent.check_bridge_port_forwarding(
        evidence, "mikrotik_routeros", bridge, interface, expected=expected
    )


def check_property(
    evidence: Mapping[str, Any],
    menu: str,
    where: Mapping[str, str],
    name: str,
    expected: str | None,
) -> IntentResult:
    """Compare one property of a `print detail` entry, `None` when it is absent.

    `menu` is the path, for example `/interface bridge port`, and the reply
    must be for `<menu> print detail ...`. `where` selects one entry by its
    properties, for example `{"interface": "ether4"}`. Values compare as
    printed, without quotes.
    """
    prefix = _canonical(f"{menu} print detail")

    def accepts(line: str) -> bool:
        return any(
            _canonical(part) == prefix or _canonical(part).startswith(prefix + " ")
            for part in line.split(";")
        )

    try:
        text = intent.reply_output(evidence, accepts, f"{menu} print detail")
        observed = _entry(text, where, name)
    except ValueError as error:
        return IntentResult(expected, None, "unavailable", str(error))
    verdict: Verdict = "match" if observed == expected else "mismatch"
    return IntentResult(expected, observed, verdict)


def check_version(evidence: Mapping[str, Any], expected: str) -> IntentResult:
    """Compare the `version` of `/system resource print`, without the channel."""
    try:
        version = _vertical(_text(evidence, RESOURCE), "version")
        if not version:
            msg = "resource print has no version"
            raise ValueError(msg)
    except ValueError as error:
        return IntentResult(expected, None, "unavailable", str(error))
    observed = version.split()[0]
    verdict: Verdict = "match" if observed == expected else "mismatch"
    return IntentResult(expected, observed, verdict)
