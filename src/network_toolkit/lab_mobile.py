# SPDX-License-Identifier: MIT
"""Move or silence an active-backup lab bond and replay proof from Ethernet captures."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from network_toolkit import lab, lab_faults, traffic

MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}")


@dataclass(frozen=True)
class ActiveMember:
    bond: str
    member: str


@dataclass(frozen=True)
class SilenceHost:
    bond: str
    clear: bool
    relearn_s: float = 0


Action = ActiveMember | SilenceHost


def _require(ok: object, text: str) -> None:
    if not ok:
        raise lab.LabError(text)


def parse(raw: Mapping[str, Any], where: str) -> Action:
    """Read one closed-schema mobile-host action."""
    fields = set(raw)
    if fields == {"active_member", "member"}:
        bond, member = raw["active_member"], raw["member"]
        _require(isinstance(member, str), f"{where}: member needs an interface name")
        # Validate the member using the same point parser as the bond.
        end = lab.point(bond) if isinstance(bond, str) else None
        _require(end is not None, f"{where}: active_member needs node:bond")
        assert end is not None
        lab.point(f"{end.node}:{member}")
        return ActiveMember(str(end), member)
    if fields in ({"silence_host", "relearn_s"}, {"silence_host", "clear"}):
        bond = raw["silence_host"]
        _require(isinstance(bond, str), f"{where}: silence_host needs node:bond")
        end = lab.point(bond)
        if "clear" in raw:
            _require(raw["clear"] is True, f"{where}: clear must be true")
            return SilenceHost(str(end), True)
        limit = raw["relearn_s"]
        _require(
            not isinstance(limit, bool)
            and isinstance(limit, (int, float))
            and math.isfinite(limit)
            and limit > 0,
            f"{where}: relearn_s needs a positive number of seconds",
        )
        return SilenceHost(str(end), False, float(limit))
    msg = f"{where}: use active_member with member, or silence_host with relearn_s or clear"
    raise lab.LabError(msg)


def validate(actions: Sequence[Action]) -> None:
    """Require a matching return for every move or silence."""
    pending: dict[tuple[type, str], Action] = {}
    for action in actions:
        key = (type(action), action.bond)
        first = pending.get(key)
        if isinstance(action, ActiveMember):
            if first is None:
                pending[key] = action
            else:
                assert isinstance(first, ActiveMember)
                _require(first.member != action.member, f"{action.bond} must move back")
                del pending[key]
        elif action.clear:
            _require(first is not None, f"{action.bond} needs an earlier silence")
            del pending[key]
        else:
            _require(first is None, f"{action.bond} must resume before another silence")
            pending[key] = action
    _require(not pending, "Every mobile host move or silence needs a return step")


@dataclass(frozen=True)
class Layout:
    member_points: dict[str, str]
    witnesses: dict[str, list[str]]
    address: str


def _bond_state(row: Mapping[str, Any], point: lab.Point) -> tuple[str, str]:
    """The selected member and stable MAC from the kernel's bond row."""
    info = row["linkinfo"]
    data = info["info_data"]
    member, mac = data.get("active_slave"), row["address"].lower()
    _require(
        row["ifname"] == point.interface
        and info["info_kind"] == "bond"
        and data["mode"] == "active-backup"
        and isinstance(member, str)
        and MAC.fullmatch(mac),
        f"{point} must be an active-backup bond with a selected member and valid MAC",
    )
    return member, mac


class Actions:
    """Own the selected bond member and the filters installed by this run."""

    def __init__(self, session: lab.Session) -> None:
        self.session = session
        self.topology = session.lab
        self.layouts: dict[str, Layout] = {}
        self.moves: dict[str, str] = {}
        self.silences: dict[str, set[lab.Point]] = {}

    def __enter__(self) -> Actions:
        return self

    def __exit__(
        self, _kind: object, original: BaseException | None, _traceback: object
    ) -> None:
        errors = []
        for bond, member in list(self.moves.items()):
            try:
                self.select(lab.point(bond), member)
                self.session.mark("mobile_move_restored", bond=bond, member=member)
            except Exception as error:
                errors.append(f"{bond} member return: {error}")
        for bond in list(self.silences):
            try:
                self._remove(bond)
            except Exception as error:
                errors.append(f"{bond} silence cleanup: {error}")
        self.session.record_restore_errors(errors, original)

    def points(self, actions: Sequence[Action]) -> set[str]:
        """Read the topology and select the switch TAPs and affected witness ports."""
        points: set[str] = set()
        for target in dict.fromkeys(action.bond for action in actions):
            bond = lab.point(target)
            _require(
                self.topology.node(bond.node).kind == "linux",
                f"{bond} needs a Linux node",
            )
            members = json.loads(
                self.topology.run(
                    bond.node,
                    "ip",
                    "-j",
                    "-d",
                    "link",
                    "show",
                    "master",
                    bond.interface,
                )
            )
            _require(
                len(members) == 2
                and all(
                    row.get("master") == bond.interface and "LOWER_UP" in row["flags"]
                    for row in members
                ),
                f"{bond} needs two connected members",
            )
            member_points: dict[str, str] = {}
            switches: set[str] = set()
            for row in members:
                member = row["ifname"]
                far = self.topology.peer(lab.Point(bond.node, member))
                nic = self.topology.qemu(far)
                _require(
                    nic is not None, f"{far} needs a capture TAP in a QEMU guest bridge"
                )
                assert nic is not None
                switches.add(far.node)
                member_points[member] = str(lab.Point(far.node, nic.tap))
            _require(
                len(switches) == 2, f"{bond} needs its members on different switches"
            )
            for action in actions:
                if action.bond == target and isinstance(action, ActiveMember):
                    _require(
                        action.member in member_points,
                        f"{action.member} is not a member of {bond}",
                    )
            witnesses: dict[str, list[str]] = {}
            if any(
                action.bond == target and isinstance(action, SilenceHost)
                for action in actions
            ):
                for ends in self.topology.links:
                    for host_end, switch in (ends, ends[::-1]):
                        if (
                            switch.node in switches
                            and host_end.node != bond.node
                            and self.topology.node(host_end.node).kind == "linux"
                        ):
                            witnesses.setdefault(host_end.node, []).append(
                                str(host_end)
                            )
                points.update(p for ports in witnesses.values() for p in ports)
            self.layouts[target] = Layout(
                member_points, witnesses, self.topology.ipv4(bond)
            )
            points.update(member_points.values())
        return points

    def select(self, bond: lab.Point, member: str) -> None:
        self.topology.run(
            bond.node,
            "ip",
            "link",
            "set",
            "dev",
            bond.interface,
            "type",
            "bond",
            "active_slave",
            member,
        )

    def _remove(self, target: str) -> None:
        owned = self.silences[target]
        errors = []
        for end in sorted(owned):
            try:
                raw = lab_faults._qdisc(self.topology, end)
                lab_faults._classifier_remove(self.topology, end, raw)
                owned.discard(end)
            except lab.LabError as error:
                errors.append(str(error))
        _require(not errors, "; ".join(errors))
        del self.silences[target]

    def run(self, action: Action, number: int) -> None:
        """Move the selected member or install/remove both egress classifiers."""
        bond = lab.point(action.bond)
        layout = self.layouts[action.bond]
        before = self.topology.link_state(bond)
        member, mac = _bond_state(before, bond)
        _require(
            member in layout.member_points, f"{bond} selected an unexpected member"
        )
        if isinstance(action, ActiveMember):
            self._move(action, number, bond, before, member, mac, layout)
        elif action.clear:
            self._resume(action, number, bond, layout)
        else:
            self._silence(action, number, bond, before, layout)

    def _move(
        self,
        action: ActiveMember,
        number: int,
        bond: lab.Point,
        before: dict,
        member: str,
        mac: str,
        layout: Layout,
    ) -> None:
        original = self.moves.get(action.bond)
        _require(member != action.member, f"{bond} already uses {action.member}")
        _require(
            original is None or action.member == original,
            f"{bond} must return to {original}",
        )
        self.moves.setdefault(action.bond, member)
        self.session.mark(
            "mobile_move_start",
            number=number,
            bond=action.bond,
            layout=asdict(layout),
            before=before,
            member=action.member,
        )
        self.select(bond, action.member)
        after = self.topology.link_state(bond)
        _require(
            _bond_state(after, bond) == (action.member, mac),
            f"{bond} did not move to {action.member} with its original MAC",
        )
        self.session.mark("mobile_moved", number=number, bond=action.bond, after=after)
        if original is not None:
            del self.moves[action.bond]

    def _silence(
        self,
        action: SilenceHost,
        number: int,
        bond: lab.Point,
        before: dict,
        layout: Layout,
    ) -> None:
        ends = [lab.Point(bond.node, member) for member in layout.member_points]
        qdisc_before = {str(end): lab_faults._qdisc(self.topology, end) for end in ends}
        _require(
            all(not lab_faults._has_classifier(raw) for raw in qdisc_before.values()),
            f"{bond} already has a classifier on one of its members",
        )
        self.session.mark(
            "mobile_silence_start",
            number=number,
            bond=action.bond,
            layout=asdict(layout),
            before=before,
            qdisc_before=qdisc_before,
        )
        owned: set[lab.Point] = set()
        self.silences[action.bond] = owned
        for end in ends:
            # The command can apply the classifier before an interrupt reaches Networka.
            owned.add(end)
            lab_faults._classifier_add(
                self.topology,
                end,
                "egress",
                ("protocol", "all", "pref", "43", "flower", "action", "drop"),
            )
        applied = {
            str(end): lab_faults._filter_stats(self.topology, end, "egress")
            for end in ends
        }
        _require(
            all(_drop_filter(raw) for raw in applied.values()),
            f"{bond} silence was not installed",
        )
        self.session.mark("mobile_silent", number=number, bond=action.bond, raw=applied)

    def _resume(
        self, action: SilenceHost, number: int, bond: lab.Point, layout: Layout
    ) -> None:
        ends = [lab.Point(bond.node, member) for member in layout.member_points]
        self.session.mark("mobile_resume_start", number=number, bond=action.bond)
        counters = {
            str(end): lab_faults._filter_stats(self.topology, end, "egress")
            for end in ends
        }
        self._remove(action.bond)
        after = self.topology.link_state(bond)
        restored = {str(end): lab_faults._qdisc(self.topology, end) for end in ends}
        _require(
            all(not lab_faults._has_classifier(raw) for raw in restored.values()),
            f"{bond} silence was not removed",
        )
        self.session.mark(
            "mobile_resumed",
            number=number,
            bond=action.bond,
            counters=counters,
            after=after,
            raw=restored,
        )


def _drop_filter(raw: str) -> bool:
    return "protocol all pref 43 flower" in raw and "action drop" in raw


def _event(
    events: Sequence[Mapping[str, Any]], name: str, number: int
) -> Mapping[str, Any]:
    [event] = [e for e in events if e["name"] == name and e.get("number") == number]
    return event


def _pcap(folder: Path, events: Sequence[Mapping[str, Any]], point: str) -> Path:
    [capture] = [
        e for e in events if e["name"] == "capture_started" and e["point"] == point
    ]
    [stopped] = [e for e in events if e["name"] == "stopped"]
    pcap = folder / "captures" / (lab.file_name(lab.point(point)) + ".pcap")
    _require(
        capture["pcap"] == str(pcap.relative_to(folder))
        and point not in stopped.get("early_exits", [])
        and traffic.check_capture(pcap, pcap.with_suffix(".log"))["valid"],
        f"{point} has no complete packet capture",
    )
    return pcap


def _stamps(pcap: Path, display_filter: str) -> Sequence[int]:
    rows = lab.run(
        [
            "tshark",
            "-n",
            "-r",
            str(pcap),
            "-Y",
            display_filter,
            "-T",
            "fields",
            "-e",
            "frame.time_epoch",
        ],
        timeout=traffic.TSHARK_TIMEOUT_S,
    )
    return [int(Decimal(stamp) * traffic.NS) for stamp in rows.splitlines()]


def _move_proof(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    actions: Mapping[int, Action],
    number: int,
    action: ActiveMember,
    measured: Mapping[str, Any],
) -> dict[str, Any]:
    start = _event(events, "mobile_move_start", number)
    moved = _event(events, "mobile_moved", number)
    bond = lab.point(action.bond)
    layout = Layout(**start["layout"])
    previous, mac = _bond_state(start["before"], bond)
    _require(
        start["bond"] == moved["bond"] == action.bond
        and start["member"] == action.member
        and previous != action.member
        and _bond_state(moved["after"], bond) == (action.member, mac)
        and start["mono_ns"] <= moved["mono_ns"]
        and set(layout.member_points) == {previous, action.member},
        f"{bond} saved state did not prove the requested move",
    )
    same_bond = [
        n
        for n, other in actions.items()
        if isinstance(other, ActiveMember) and other.bond == action.bond
    ]
    if same_bond.index(number) % 2:
        opening = _event(
            events, "mobile_move_start", same_bond[same_bond.index(number) - 1]
        )
        _require(
            _bond_state(opening["before"], bond) == (action.member, mac),
            f"{bond} did not return to its original member",
        )
    end = next(
        (
            e["epoch_ns"]
            for e in events
            if e["name"] == "mobile_move_start"
            and e["bond"] == action.bond
            and e["number"] > number
        ),
        measured["end_ns"],
    )
    new, old = (
        _pcap(folder, events, layout.member_points[member])
        for member in (action.member, previous)
    )
    address = layout.address
    _require(
        re.fullmatch(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", address),
        f"{bond} has no valid captured IPv4 address",
    )
    arps = _stamps(
        new,
        f"eth.src == {mac} && eth.dst == ff:ff:ff:ff:ff:ff && "
        f"arp.src.proto_ipv4 == {address} && arp.dst.proto_ipv4 == {address}",
    )
    arrival = next((stamp for stamp in arps if start["epoch_ns"] <= stamp < end), None)
    _require(
        arrival is not None,
        f"The gratuitous ARP was not captured at {layout.member_points[action.member]}",
    )
    assert arrival is not None
    leaked = sum(arrival <= stamp < end for stamp in _stamps(old, f"eth.dst == {mac}"))
    proof = {
        "verdict": "fail" if leaked else "pass",
        "bond": action.bond,
        "from": previous,
        "to": action.member,
        "old_point": layout.member_points[previous],
        "new_point": layout.member_points[action.member],
        "gratuitous_arp_s": traffic.seconds(arrival - measured["start_ns"]),
        "old_port_unicast_after_garp": leaked,
    }
    if leaked:
        proof["reason"] = (
            f"{leaked} frames addressed to {mac} used the old TAP after the gratuitous ARP"
        )
    return proof


def _affected(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    measured: Mapping[str, Any],
    bond: str,
    applied: int,
    cleared: int,
    first: int,
    end: int,
    limit: float,
) -> tuple[dict[str, Any], list[str]]:
    """Verify the loss and the first recovered reply on every stream using the host."""
    details: dict[str, Any] = {}
    failures = []
    zero = measured["start_ns"]
    for name, measured_stream in measured["streams"].items():
        if bond not in (measured_stream["source"], measured_stream["destination"]):
            continue
        outages = [
            outage
            for outage in measured_stream["outages"]
            if outage["begins_s"] <= traffic.seconds(cleared - zero)
            and outage["ends_s"] >= traffic.seconds(applied - zero)
        ]
        _require(
            outages and all(not outage["absent_at_source"] for outage in outages),
            f"{name} did not show a delivery outage with requests still sent during silence",
        )
        pcap = _pcap(folder, events, measured_stream["source"])
        reply = next(
            (
                stamp
                for stamp in _stamps(
                    pcap, f"icmp.ident == {measured_stream['ident']} && icmp.type == 0"
                )
                if first <= stamp < end
            ),
            None,
        )
        delay = traffic.seconds(reply - first) if reply is not None else None
        details[name] = {"first_reply_s": delay, "limit_s": limit}
        if reply is None or delay is None or delay > limit:
            failures.append(
                f"{name} did not deliver again within {limit:g} s of the first host frame"
            )
        elif any(
            traffic.seconds(reply - zero)
            <= outage["begins_s"]
            < traffic.seconds(end - zero)
            for outage in measured_stream["outages"]
        ):
            failures.append(f"{name} lost another ping after delivery resumed")
    _require(details, f"No measured stream uses {bond}")
    return details, failures


def _flooding(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    measured: Mapping[str, Any],
    layout: Layout,
    bond: str,
    mac: str,
    applied: int,
    cleared: int,
    first: int,
    window: tuple[int, int],
    limit: float,
) -> tuple[dict[str, Any], list[str]]:
    """Count mobile-bound requests received at the other hosts' switch-facing ports."""
    details: dict[str, Any] = {}
    failures = []
    begin, end = window
    for name, measured_stream in measured["streams"].items():
        if measured_stream["destination"] != bond:
            continue
        sender = lab.point(measured_stream["source"]).node
        witnesses = [
            point
            for node, points in layout.witnesses.items()
            if node != sender
            for point in points
        ]
        _require(witnesses, f"{name} has no host ports witnessing possible flooding")
        display = f"eth.dst == {mac} && icmp.ident == {measured_stream['ident']} && icmp.type == 8"
        seen = [
            stamp
            for point in witnesses
            for stamp in _stamps(_pcap(folder, events, point), display)
            if begin <= stamp < end
        ]
        after = [stamp for stamp in seen if stamp >= first]
        delay = traffic.seconds(max(after) - first) if after else 0.0
        details[name] = {
            "captures": witnesses,
            "before_silence": sum(stamp < applied for stamp in seen),
            "while_silent": sum(applied <= stamp < cleared for stamp in seen),
            "after_first_frame": len(after),
            "last_flood_after_first_frame_s": delay,
            "limit_s": limit,
        }
        if delay > limit:
            failures.append(
                f"{name} still flooded {delay:g} s after the host's first frame"
            )
    _require(details, f"No mobile-bound stream proves forwarding to {bond}")
    return details, failures


def _silence_proof(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    actions: Mapping[int, Action],
    number: int,
    action: SilenceHost,
    measured: Mapping[str, Any],
) -> dict[str, Any]:
    indices = [
        n
        for n, other in actions.items()
        if isinstance(other, SilenceHost) and other.bond == action.bond
    ]
    position = indices.index(number) - action.clear
    opening, closing = indices[position : position + 2]
    start = _event(events, "mobile_silence_start", opening)
    silent = _event(events, "mobile_silent", opening)
    clear = _event(events, "mobile_resume_start", closing)
    resumed = _event(events, "mobile_resumed", closing)
    original = actions[opening]
    assert isinstance(original, SilenceHost)
    layout = Layout(**start["layout"])
    bond = lab.point(action.bond)
    member, mac = _bond_state(start["before"], bond)
    points = {str(lab.Point(bond.node, member)) for member in layout.member_points}
    _require(
        all(e["bond"] == action.bond for e in (start, silent, clear, resumed))
        and start["mono_ns"]
        <= silent["mono_ns"]
        < clear["mono_ns"]
        <= resumed["mono_ns"]
        and set(start["qdisc_before"])
        == set(silent["raw"])
        == set(resumed["raw"])
        == set(resumed["counters"])
        == points
        and len(points) == 2
        and all(_drop_filter(raw) for raw in silent["raw"].values())
        and all(_drop_filter(raw) for raw in resumed["counters"].values())
        and all(
            not lab_faults._has_classifier(raw)
            for raw in (*start["qdisc_before"].values(), *resumed["raw"].values())
        )
        and _bond_state(resumed["after"], bond) == (member, mac),
        f"{bond} saved state did not prove both egress filters and their removal",
    )
    drops = {
        point: lab_faults._drop_count(raw)
        for point, raw in sorted(resumed["counters"].items())
    }
    _require(
        drops[str(lab.Point(bond.node, member))] > 0,
        f"{bond} recorded no drops on its active member",
    )
    frames = sorted(
        stamp
        for member_point in layout.member_points.values()
        for stamp in _stamps(_pcap(folder, events, member_point), f"eth.src == {mac}")
    )
    applied, cleared = silent["epoch_ns"], clear["epoch_ns"]
    previous_resume = max(
        (
            event["epoch_ns"]
            for event in events
            if event["name"] == "mobile_resumed"
            and event["bond"] == action.bond
            and event["number"] < opening
        ),
        default=measured["start_ns"],
    )
    end = min(
        (
            event["epoch_ns"]
            for event in events
            if event["name"] in ("mobile_move_start", "mobile_silence_start")
            and event["bond"] == action.bond
            and event["number"] > closing
        ),
        default=measured["end_ns"],
    )
    _require(
        any(stamp < applied for stamp in frames)
        and not any(applied <= stamp < cleared for stamp in frames),
        "The switch TAPs did not prove the host sent before the cut and was silent during it",
    )
    first = next((stamp for stamp in frames if cleared <= stamp < end), None)
    _require(
        first is not None,
        f"No frame from {bond} reached a switch TAP after the silence",
    )
    assert first is not None
    delivery, failed_delivery = _affected(
        folder,
        events,
        measured,
        action.bond,
        applied,
        cleared,
        first,
        end,
        original.relearn_s,
    )
    flooding, failed_flooding = _flooding(
        folder,
        events,
        measured,
        layout,
        action.bond,
        mac,
        applied,
        cleared,
        first,
        (previous_resume, end),
        original.relearn_s,
    )
    problems = failed_delivery + failed_flooding
    result = {
        "verdict": "fail" if problems else "pass",
        "bond": action.bond,
        "dropped": drops,
        "points": layout.member_points,
        "held_s": traffic.seconds(clear["mono_ns"] - silent["mono_ns"]),
        "first_host_frame_s": traffic.seconds(first - measured["start_ns"]),
        "delivery": delivery,
        "flooding": flooding,
    }
    if problems:
        result["reason"] = "; ".join(problems)
    return result


def proof(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    actions: Mapping[int, Action],
    number: int,
    measured: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the mobile action against its raw state and packet evidence."""
    action = actions[number]
    try:
        if isinstance(action, ActiveMember):
            return _move_proof(folder, events, actions, number, action, measured)
        return _silence_proof(folder, events, actions, number, action, measured)
    except (
        OSError,
        KeyError,
        ValueError,
        TypeError,
        IndexError,
        lab.LabError,
    ) as error:
        return {"verdict": "error", "bond": action.bond, "reason": str(error)}


def event_row(event: Mapping[str, Any]) -> tuple[str, str] | None:
    name = event["name"]
    if name == "mobile_move_start":
        return "mobile host", f"{event['bond']} moves to {event['member']}"
    if name == "mobile_silent":
        return (
            "mobile host",
            f"{event['bond']} egress filters installed on both members",
        )
    if name == "mobile_resumed":
        return "mobile host", f"{event['bond']} egress filters removed"
    if name == "mobile_move_restored":
        return "mobile host", f"{event['bond']} restored to {event['member']}"
    return None
