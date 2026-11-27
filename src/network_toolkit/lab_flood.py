# SPDX-License-Identifier: MIT
"""The flood check: broadcast and unknown-unicast frames must not return to their sender."""

from __future__ import annotations

import ipaddress
import itertools
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from network_toolkit import intent, lab, traffic


@dataclass(frozen=True)
class Flood:
    source: str
    receiver: str
    broadcast: str
    unicast: str
    unicast_mac: str


def parse(raw: Mapping[str, str]) -> Flood:
    mac = intent.mac(raw["unicast_mac"])
    if int(mac[:2], 16) & 3 != 2:
        msg = "unicast_mac must be a locally administered unicast address reserved for this lab"
        raise ValueError(msg)
    return Flood(
        str(lab.point(raw["from"])),
        str(lab.point(raw["to"])),
        str(ipaddress.IPv4Address(raw["broadcast"])),
        str(ipaddress.IPv4Address(raw["unicast"])),
        mac,
    )


def _require(ok: object, message: str) -> None:
    if not ok:
        raise lab.LabError(message)


def _networks(raw: str, interface: str) -> list[ipaddress.IPv4Interface]:
    [row] = json.loads(raw)
    _require(row["ifname"] == interface, f"Address readback does not name {interface}")
    return [
        ipaddress.IPv4Interface(f"{info['local']}/{info['prefixlen']}")
        for info in row["addr_info"]
        if info["family"] == "inet"
    ]


def _members(spec: Flood, readings: Mapping[str, str]) -> tuple[lab.Point, ...]:
    source, receiver = lab.point(spec.source), lab.point(spec.receiver)
    [bond] = json.loads(readings["bond"])
    info = bond["linkinfo"]
    _require(
        bond["ifname"] == source.interface
        and info["info_kind"] == "bond"
        and info["info_data"]["mode"] == "802.3ad",
        f"{source} must be an 802.3ad bond",
    )
    rows = json.loads(readings["members"])
    members = tuple(lab.Point(source.node, row["ifname"]) for row in rows)
    _require(
        len(set(members)) == len(rows) == 2
        and all(
            r["master"] == source.interface and "LOWER_UP" in r["flags"] for r in rows
        ),
        f"{source} must have both lab cable members connected",
    )
    source_ips = _networks(readings["addresses"], source.interface)
    receiver_ips = _networks(readings["receiver"], receiver.interface)
    target = ipaddress.IPv4Address(spec.unicast)
    _require(
        any(
            str(address.network.broadcast_address) == spec.broadcast
            and target in address.network
            and target != address.network.network_address
            and any(peer.network == address.network for peer in receiver_ips)
            for address in source_ips
        )
        and target not in {r.ip for r in (*source_ips, *receiver_ips)}
        and spec.unicast != spec.broadcast,
        "The flood destinations must identify the source subnet broadcast and an unused address in it",
    )
    [neighbour] = json.loads(readings["neighbour"])
    _require(
        neighbour["dst"] == spec.unicast
        and neighbour["lladdr"] == spec.unicast_mac
        and "PERMANENT" in neighbour["state"],
        f"{source} needs a permanent neighbour for {spec.unicast} at {spec.unicast_mac}",
    )
    return members


def preflight(session: lab.Session, spec: Flood) -> tuple[lab.Point, ...]:
    """Read the sender, witness, and permanent neighbour from the deployed lab."""
    topology = session.lab
    source, receiver = lab.point(spec.source), lab.point(spec.receiver)
    _require(
        source.node != receiver.node
        and all(topology.node(p.node).kind == "linux" for p in (source, receiver)),
        "A flood check needs distinct Linux lab nodes for sender and receiver",
    )
    readings = {
        "bond": topology.run(
            source.node, "ip", "-j", "-d", "link", "show", "dev", source.interface
        ),
        "members": topology.run(
            source.node, "ip", "-j", "-d", "link", "show", "master", source.interface
        ),
        "addresses": topology.run(
            source.node, "ip", "-j", "-4", "addr", "show", "dev", source.interface
        ),
        "receiver": topology.run(
            receiver.node, "ip", "-j", "-4", "addr", "show", "dev", receiver.interface
        ),
        "neighbour": topology.run(
            source.node,
            "ip",
            "-j",
            "-4",
            "neigh",
            "show",
            "to",
            spec.unicast,
            "dev",
            source.interface,
        ),
    }
    members = _members(spec, readings)
    for member in members:
        topology.peer(member)
    session.mark("flood_ready", readings=readings)
    return members


def _flood_streams(spec: Flood, first_ident: int) -> tuple[tuple[str, int, str], ...]:
    return (
        ("_flood-broadcast", first_ident, spec.broadcast),
        ("_flood-unknown-unicast", first_ident + 1, spec.unicast),
    )


def start(session: lab.Session, spec: Flood, first_ident: int) -> None:
    for name, ident, destination in _flood_streams(spec, first_ident):
        session.start_stream(
            ident,
            name,
            spec.source,
            destination,
            traffic.INTERVAL_NS / traffic.NS,
            address=destination,
            broadcast=destination == spec.broadcast,
        )


def _count_frames(
    frames: Mapping[str, traffic.Frames],
    spec: Flood,
    members: tuple[lab.Point, ...],
    ident: int,
    start: int,
    end: int,
    quiet_end: int,
) -> dict[str, Any]:
    source = frames[spec.source]
    receiver = frames[spec.receiver]
    sent = {
        frame: stamps[0]
        for frame, stamps in source.items()
        if frame[:2] == (ident, traffic.REQUEST) and stamps and start <= stamps[0] < end
    }
    stamps = [start, *sorted(sent.values()), end]
    pause = max(b - a for a, b in itertools.pairwise(stamps))
    verified = [sent_frame for sent_frame, stamp in sent.items() if stamp < quiet_end]
    appearances = {
        sent_frame: sum(
            len(frames[str(member)].get(sent_frame, ())) for member in members
        )
        for sent_frame in sent
    }
    returns = [
        sent_frame[2][0] for sent_frame, count in appearances.items() if count > 1
    ]
    quiet_other = [
        sent_frame[2][0]
        for sent_frame in verified
        if appearances[sent_frame] != 1 or len(receiver.get(sent_frame, ())) != 1
    ]
    # Measure at least one second of clean flooded frames before the first action.
    if len(verified) < 10 or pause > traffic.SEND_GAP_LIMIT_NS:
        verdict, reason = "error", "Too few regularly numbered flood frames were sent."
    elif returns:
        verdict, reason = (
            "fail",
            "A frame was seen more than once across the sender's bond members.",
        )
    elif quiet_other:
        verdict, reason = (
            "fail",
            "A frame of the quiet window did not appear once at the sender and receiver.",
        )
    else:
        verdict, reason = "pass", None
    return {
        "verdict": verdict,
        "reason": reason,
        "sent": len(sent),
        "quiet_sent": len(verified),
        "quiet_exceptions": quiet_other,
        "max_send_interval_s": traffic.seconds(pause),
        "sender_returns": returns,
    }


def quiet_problems(
    spec: Flood,
    captures: Mapping[str, Path],
    members: tuple[lab.Point, ...],
    first_ident: int,
    start_ns: int,
    end_ns: int,
) -> list[str]:
    """Require a working flood check and a clean witness before mutating the lab."""
    frames = {
        point: traffic.decode(captures[point])
        for point in (spec.source, spec.receiver, *(str(member) for member in members))
    }
    failures = []
    for _, ident, destination in _flood_streams(spec, first_ident):
        result = _count_frames(frames, spec, members, ident, start_ns, end_ns, end_ns)
        if result["verdict"] != "pass":
            failures.append(f"flood check to {destination}: {result['reason']}")
    return failures


def proof(
    spec: Flood,
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    first_ident: int,
    start_ns: int,
    end_ns: int,
    quiet_end: int,
) -> dict[str, Any]:
    """Verify sound captures and replay membership, quiet window witnesses and returns."""
    result: dict[str, Any] = {
        "source": spec.source,
        "receiver": spec.receiver,
        "verdict": "error",
        "frames": [],
    }
    try:
        [ready] = [e for e in events if e["name"] == "flood_ready"]
        [stopped] = [e for e in events if e["name"] == "stopped"]
        members = _members(spec, ready["readings"])
        result["members"] = [str(member) for member in members]
        points = {spec.source, spec.receiver, *result["members"]}
        captures = {
            e["point"]: folder / e["pcap"]
            for e in events
            if e["name"] == "capture_started" and e["point"] in points
        }
        _require(set(captures) == points, "A required flood capture is missing")
        for point, capture in captures.items():
            valid = traffic.check_capture(capture, capture.with_suffix(".log"))
            _require(
                valid["valid"],
                f"The flood capture at {point} is incomplete or dropped packets",
            )
        frames = {point: traffic.decode(capture) for point, capture in captures.items()}
        for name, ident, destination in _flood_streams(spec, first_ident):
            [began] = [
                e
                for e in events
                if e["name"] == "stream_started" and e["stream"] == name
            ]
            _require(
                began["ident"] == ident
                and began["source"] == spec.source
                and began["address"] == destination
                and name not in stopped["early_exits"]
                and not points.intersection(stopped["early_exits"]),
                f"Flood check to {destination} or one of its captures did not run throughout the test",
            )
            result["frames"].append(
                {
                    "destination": destination,
                    "ident": ident,
                    **_count_frames(
                        frames, spec, members, ident, start_ns, end_ns, quiet_end
                    ),
                }
            )
    except (
        OSError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        lab.LabError,
        subprocess.SubprocessError,
    ) as error:
        result["reason"] = str(error)
        return result
    bad = [
        sent_frame for sent_frame in result["frames"] if sent_frame["verdict"] != "pass"
    ]
    if bad:
        result["verdict"] = (
            "fail"
            if any(sent_frame["verdict"] == "fail" for sent_frame in bad)
            else "error"
        )
        result["reason"] = "; ".join(f"{p['destination']} {p['reason']}" for p in bad)
    else:
        result["verdict"] = "pass"
    return result
