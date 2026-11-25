# SPDX-License-Identifier: MIT
"""Check RouterOS bridge-port forwarding from native JSON replies.

`collect_bridge_port` reads the port statistics and the selected port's
monitor reply through a `NetworkaClient`. It keeps each command with its
output or error. `check_bridge_port_forwarding` evaluates that evidence
offline, so a saved capture gives the same verdict when replayed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from network_toolkit.client import NetworkaClient

_JSON = ":put [:serialize to=json options=json.no-string-conversion [{}]]"
PORT_STATS = _JSON.format("/interface/bridge/port/print stats as-value")
PORT_MONITOR = _JSON.format("/interface/bridge/port/monitor {port_id} once as-value")

Verdict = Literal["match", "mismatch", "unavailable"]


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

    expected: bool
    observed: bool | None
    verdict: Verdict
    reason: str | None = None


def _read(
    client: NetworkaClient, device: str, command: str, run_options: dict[str, Any]
) -> Reply:
    try:
        result = client.run(device, command, **run_options)
    except NetworkToolkitError as error:
        return {"command": command, "output": None, "error": error.message}
    rows = [row for row in result.command_results if row.device == device]
    if len(rows) != 1:
        msg = f"expected one command result for {device}, got {len(rows)}"
        return {"command": command, "output": None, "error": msg}
    return {"command": command, "output": rows[0].output, "error": rows[0].error}


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
    """Read the replies that `check_bridge_port_forwarding` evaluates.

    Read failures are kept in the evidence instead of raised. `run_options`
    are passed to `NetworkaClient.run`, for example `interactive_creds`.
    The monitor reply is absent when the port cannot be selected.
    """
    evidence = {"stats": _read(client, device, PORT_STATS, run_options)}
    try:
        port_id = _port_id(_output(evidence, "stats", PORT_STATS), bridge, interface)
    except ValueError:
        return evidence
    monitor = PORT_MONITOR.format(port_id=port_id)
    evidence["monitor"] = _read(client, device, monitor, run_options)
    return evidence


def check_bridge_port_forwarding(
    evidence: Mapping[str, Any], bridge: str, interface: str, expected: bool = True
) -> IntentResult:
    """Compare the monitor `forwarding` Boolean of one bridge port.

    The port is selected by bridge and interface name in the statistics, and
    the monitor reply must carry the same `.id`. A read error, invalid JSON,
    an ambiguous port, or a missing field gives `unavailable`.
    """
    try:
        port_id = _port_id(_output(evidence, "stats", PORT_STATS), bridge, interface)
        command = PORT_MONITOR.format(port_id=port_id)
        port = json.loads(_output(evidence, "monitor", command))
        if not isinstance(port, dict) or port.get(".id") != port_id:
            msg = "monitor reply does not identify the selected port"
            raise ValueError(msg)
        observed = port.get("forwarding")
        if not isinstance(observed, bool):
            msg = "monitor forwarding is missing or is not a JSON Boolean"
            raise ValueError(msg)
    except ValueError as error:
        return IntentResult(expected, None, "unavailable", str(error))
    verdict: Verdict = "match" if observed is expected else "mismatch"
    return IntentResult(expected, observed, verdict)
