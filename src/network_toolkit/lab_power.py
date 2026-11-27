# SPDX-License-Identifier: MIT
"""Abrupt power loss and recovery of containerlab nodes: RouterOS CHR guests and Linux hosts."""

from __future__ import annotations

import ipaddress
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from network_toolkit import intent, lab, lab_reboot
from network_toolkit.platforms.mikrotik_routeros import intent as routeros
from network_toolkit.traffic import NS

if TYPE_CHECKING:
    from network_toolkit.client import NetworkaClient

# Replies of every monitor command that the evidence keeps per RouterOS guest.
GUEST_REPLIES = ("uptime", "status", "stop", "system_reset", "cont")


@dataclass(frozen=True)
class Power:
    """Power off or on one node, an inventory group, or the listed `nodes`.

    `target` is the node or group as written, or the listed nodes joined by commas.
    """

    target: str
    on: bool
    nodes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Layout:
    nodes: tuple[str, ...]
    own: tuple[lab.Point, ...]
    far: tuple[lab.Point, ...]
    guests: Mapping[str, lab.Qemu]
    peers: Mapping[lab.Point, lab.Qemu]


@dataclass
class Outage:
    layout: Layout
    opening: int
    before_ns: Mapping[str, int]
    links: set[lab.Point] = field(default_factory=set)
    nics: set[lab.Point] = field(default_factory=set)
    reset_pending: set[str] = field(default_factory=set)
    resume_pending: set[str] = field(default_factory=set)


def ends(
    topology: lab.Lab, nodes: Iterable[str]
) -> tuple[tuple[lab.Point, ...], tuple[lab.Point, ...]]:
    """The cable ends on the powered nodes and the ends that face them from other nodes."""
    powered = set(nodes)
    own, far = [], []
    for left, right in topology.links:
        for end, peer in ((left, right), (right, left)):
            if end.node in powered:
                own.append(end)
                if peer.node not in powered:
                    far.append(peer)
    return tuple(own), tuple(far)


def _need(ok: object, message: str) -> None:
    if not ok:
        raise lab.LabError(message)


def resolve(
    client: NetworkaClient, topology: lab.Lab, action: Power
) -> tuple[str, ...]:
    """The lab nodes of a power action: the listed nodes, a group's members or one node."""
    if action.nodes:
        nodes = action.nodes
    elif action.target in client.groups and action.target not in topology.nodes:
        nodes = tuple(client.config.get_group_members(action.target))
        _need(nodes, f"Power group {action.target!r} has no devices")
    else:
        nodes = (action.target,)
    for node in nodes:
        topology.node(node)
    return nodes


def _nic(topology: lab.Lab, end: lab.Point) -> lab.Qemu:
    qemu = topology.qemu(end)
    if qemu is None:
        msg = f"{end} has no QEMU guest NIC"
        raise lab.LabError(msg)
    _need(
        ipaddress.ip_address(qemu.qmp_host).is_loopback
        and re.fullmatch(r"nic[1-9]\d*", qemu.nic)
        and qemu.tap == f"tap{qemu.nic[3:]}",
        f"{end} does not map to a RouterOS data NIC and loopback QEMU monitor",
    )
    return qemu


def layout(topology: lab.Lab, nodes: Sequence[str]) -> Layout:
    """Discover all data links from the deployed topology and guest NIC layout.

    A RouterOS CHR node has one QEMU guest behind all its cables. A Linux node
    has no guest; its cables alone lose carrier.
    """
    own, far = ends(topology, nodes)
    guests = {}
    for node in nodes:
        cables = [end for end in own if end.node == node]
        _need(cables, f"{node} has no data cables in the lab")
        kind = topology.node(node).kind
        if kind == "mikrotik_chr":
            nics = [_nic(topology, end) for end in cables]
            _need(
                len({(nic.pid, nic.qmp_host, nic.qmp_port) for nic in nics}) == 1,
                f"{node} does not have one guest behind all its data cables",
            )
            guests[node] = nics[0]
        else:
            _need(kind == "linux", f"{node} is neither a RouterOS CHR nor a Linux node")
    peers = {}
    for end in far:
        kind = topology.node(end.node).kind
        if kind == "mikrotik_chr":
            peers[end] = _nic(topology, end)
        else:
            _need(kind == "linux", f"{end} is not a supported power-loss neighbour")
    return Layout(tuple(nodes), own, far, guests, peers)


def _interface(nic: str) -> str:
    return f"ether{int(nic[3:]) + 1}"


def _status(reply: Mapping[str, Any], *, running: bool) -> bool:
    expected = "running" if running else "paused"
    state = reply["reply"]["return"]
    return (
        _command(reply, "query-status", {})
        and state["running"] is running
        and state["status"] == expected
    )


def _command(reply: Mapping[str, Any], execute: str, arguments: dict) -> bool:
    return (
        reply["request"]["execute"] == execute
        and reply["request"]["arguments"] == arguments
        and reply["reply"].get("id") == reply["request"].get("id") == 2
        and "return" in reply["reply"]
    )


def _carrier(
    reading: Mapping[str, Any],
    own: Sequence[lab.Point],
    far: Sequence[lab.Point],
    peers: Mapping[lab.Point, str],
    *,
    up: bool,
) -> bool:
    flags = reading["flags"]
    if set(flags) != {str(end) for end in (*own, *far)}:
        return False
    for end in (*own, *far):
        found = flags[str(end)]
        if ("LOWER_UP" in found) != up or ("UP" in found) != (up or end in far):
            return False
    guest = reading["carrier"]
    return set(guest) == {str(end) for end in peers} and all(
        routeros.interface_up(guest[str(end)], _interface(nic)) == up
        for end, nic in peers.items()
    )


def _parallel(calls: Sequence[Callable[[], Any]]) -> list[Any]:
    """Run local commands at once, so every cable of a site changes together."""
    if not calls:
        return []
    with ThreadPoolExecutor(max_workers=len(calls)) as jobs:
        futures = [jobs.submit(call) for call in calls]
        errors = [error for job in futures if (error := job.exception())]
        if errors:
            raise lab.LabError("; ".join(str(error) for error in errors))
        return [job.result() for job in futures]


class PowerActions:
    """Stop and reset guests and withdraw carrier, preserving containers, management and links."""

    def __init__(
        self,
        client: NetworkaClient,
        session: lab.Session,
        layouts: Mapping[str, Layout],
        options: Mapping[str, Any],
    ) -> None:
        self.client = client
        self.session = session
        self.layouts = layouts
        self.options = options
        self.active: dict[str, Outage] = {}

    def __enter__(self) -> PowerActions:
        return self

    def __exit__(
        self, _kind: object, original: BaseException | None, _traceback: object
    ) -> None:
        errors = []
        for target, outage in self.active.items():
            try:
                self.restore(outage)
                status = self._status(outage.layout)
                for node, reply in status.items():
                    _need(_status(reply, running=True), f"{node} did not resume")
                self._observe(outage.layout, up=True)
                self.session.mark(
                    "power_cleanup", switch=target, nodes=list(outage.layout.nodes)
                )
            except Exception as error:
                errors.append(f"{target} power cleanup: {error}")
        self.session.record_restore_errors(errors, original)

    def _link(self, end: lab.Point, *, up: bool) -> None:
        state = "up" if up else "down"
        self.session.lab.run(end.node, "ip", "link", "set", "dev", end.interface, state)

    def _links(self, ends: Iterable[lab.Point], *, up: bool) -> None:
        _parallel([partial(self._link, end, up=up) for end in sorted(ends)])

    def _facing(
        self, plan: Layout, ends: Iterable[lab.Point], *, up: bool
    ) -> dict[str, Any]:
        """Set the guest NICs that face the powered nodes; return the replies in layout order."""
        wanted = set(ends)
        chosen = [end for end in plan.peers if end in wanted]
        replies = _parallel(
            [
                partial(
                    lab.qmp_command,
                    plan.peers[end],
                    "set_link",
                    {"name": plan.peers[end].nic, "up": up},
                )
                for end in chosen
            ]
        )
        return {str(end): reply for end, reply in zip(chosen, replies, strict=True)}

    def _status(self, plan: Layout) -> dict[str, Any]:
        return {
            node: lab.qmp_command(guest, "query-status", {})
            for node, guest in plan.guests.items()
        }

    def _read(self, plan: Layout) -> dict[str, Any]:
        return {
            "flags": {
                str(end): self.session.lab.link_state(end)["flags"]
                for end in (*plan.own, *plan.far)
            },
            "carrier": {
                str(end): routeros.collect_interface(
                    self.client, end.node, _interface(nic.nic), **self.options
                )
                for end, nic in plan.peers.items()
            },
        }

    def _observe(self, plan: Layout, *, up: bool) -> dict[str, Any]:
        deadline = time.monotonic() + lab.CONFIRM_TIMEOUT_S
        peers = {end: nic.nic for end, nic in plan.peers.items()}
        while True:
            reading = self._read(plan)
            if _carrier(reading, plan.own, plan.far, peers, up=up):
                return reading
            _need(
                time.monotonic() < deadline,
                f"Data cables did not show carrier {'up' if up else 'down'}: {reading}",
            )
            # Poll faster than one ping interval to see carrier settle.
            time.sleep(0.03)

    def off(self, target: str, number: int) -> None:
        plan = self.layouts[target]
        uptime, before_ns = {}, {}
        for node in plan.guests:
            uptime[node] = routeros.collect_uptime(self.client, node, **self.options)
            before_ns[node] = routeros.uptime_ns(uptime[node])
            _need(
                before_ns[node] > 0,
                f"Cannot prove a lower uptime after power loss of {node}",
            )
        status = self._status(plan)
        for node, reply in status.items():
            _need(_status(reply, running=True), f"{node} is not running")
        baseline = self._observe(plan, up=True)
        active = Outage(plan, number, before_ns)
        self.active[target] = active
        self.session.mark(
            "power_off_start",
            switch=target,
            number=number,
            nodes=list(plan.nodes),
            uptime=uptime,
            peers={str(end): nic.nic for end, nic in plan.peers.items()},
            status=status,
            **baseline,
        )
        # A command may succeed before an interrupt or a transport error reaches us.
        active.reset_pending.update(plan.guests)
        active.resume_pending.update(plan.guests)
        stop = {
            node: lab.qmp_command(guest, "stop", {})
            for node, guest in plan.guests.items()
        }
        active.links.update(plan.own)
        self._links(plan.own, up=False)
        active.nics.update(plan.peers)
        facing = self._facing(plan, plan.peers, up=False)
        status = self._status(plan)
        for node, reply in status.items():
            _need(_status(reply, running=False), f"{node} did not pause")
        reading = self._observe(plan, up=False)
        self.session.mark(
            "power_off_observed",
            switch=target,
            number=number,
            nodes=list(plan.nodes),
            stop=stop,
            status=status,
            facing=facing,
            **reading,
        )

    def restore(self, active: Outage) -> dict[str, Any]:
        """Always attempt every guest reset and resume and every link, even after one failure."""
        plan = active.layout
        errors = []
        replies: dict[str, Any] = {"facing": {}, "system_reset": {}, "cont": {}}
        for pending, command in (
            (active.reset_pending, "system_reset"),
            (active.resume_pending, "cont"),
        ):
            for node, guest in plan.guests.items():
                if node not in pending:
                    continue
                try:
                    replies[command][node] = lab.qmp_command(guest, command, {})
                    pending.discard(node)
                except lab.LabError as error:
                    errors.append(str(error))
        for change in (self._restore_links, self._restore_nics):
            try:
                change(active, replies)
            except lab.LabError as error:
                errors.append(str(error))
        if errors:
            msg = "; ".join(errors)
            raise lab.LabError(msg)
        return replies

    def _restore_links(self, active: Outage, _replies: dict[str, Any]) -> None:
        self._links(active.links, up=True)
        active.links.clear()

    def _restore_nics(self, active: Outage, replies: dict[str, Any]) -> None:
        replies["facing"] = self._facing(active.layout, active.nics, up=True)
        active.nics.clear()

    def on(
        self, target: str, number: int, wait_s: float, items: list[intent.IntentItem]
    ) -> None:
        active = self.active[target]
        plan = active.layout
        status = self._status(plan)
        for node, reply in status.items():
            _need(_status(reply, running=False), f"{node} did not remain paused")
        dispatch = self.session.mark(
            "power_on_start",
            switch=target,
            number=number,
            nodes=list(plan.nodes),
            opening=active.opening,
            status=status,
        )
        with lab_reboot._deadline(wait_s, since_ns=dispatch["mono_ns"]):
            replies = self.restore(active)
            status = self._status(plan)
            for node, reply in status.items():
                _need(_status(reply, running=True), f"{node} did not resume")
            reading = self._observe(plan, up=True)
            self.session.mark(
                "power_on_observed",
                switch=target,
                number=number,
                nodes=list(plan.nodes),
                status=status,
                **replies,
                **reading,
            )
            lab_reboot.wait_uptime(
                self.client,
                self.session,
                active.before_ns,
                number,
                dispatch,
                self.options,
                "power",
            )
            lab_reboot.wait_healthy(
                self.client, self.session, target, number, items, self.options, "power"
            )
        del self.active[target]


def _event(
    events: Sequence[Mapping[str, Any]],
    name: str,
    switch: str,
    number: int,
) -> Mapping[str, Any]:
    matches = [
        e
        for e in events
        if e["name"] == name and e.get("switch") == switch and e.get("number") == number
    ]
    _need(
        len(matches) == 1,
        f"Expected one {name} for {switch} at step {number}, found {len(matches)}",
    )
    return matches[0]


def _per_node(event: Mapping[str, Any], node: str) -> Mapping[str, Any]:
    """An event saved when power took one switch, with its replies keyed by that switch."""
    return {
        **event,
        "nodes": [node],
        **{key: {node: event[key]} for key in GUEST_REPLIES if key in event},
    }


def proof(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    action: Power,
    opening: int,
    closing: int,
    hold_s: float,
    wait_s: float,
    items: list[intent.IntentItem],
) -> dict[str, Any]:
    """Prove the guest pauses, loss of carrier, resets, new uptimes and healthy lab."""
    target = action.target
    result: dict[str, Any] = {"switch": target, "verdict": "error", "limit_s": wait_s}
    try:
        recorded = [
            _event(events, "power_off_start", target, opening),
            _event(events, "power_off_observed", target, opening),
            _event(events, "power_on_start", target, closing),
            _event(events, "power_on_observed", target, closing),
        ]
        if "nodes" not in recorded[0]:
            recorded = [_per_node(e, target) for e in recorded]
        start, stopped, dispatch, powered = recorded
        topology = lab.parse_topology(
            json.loads((folder / lab.TOPOLOGY_DATA).read_text())
        )
        nodes = tuple(start["nodes"])
        own, far = ends(topology, nodes)
        kinds = {node: topology.node(node).kind for node in nodes}
        guests = [node for node in nodes if kinds[node] == "mikrotik_chr"]
        peers = {lab.point(p): nic for p, nic in start["peers"].items()}
        # A group is resolved from the inventory, so replay can only check the nodes it names.
        _need(
            all(e["nodes"] == list(nodes) for e in recorded)
            and (
                nodes == action.nodes
                if action.nodes
                else nodes == (target,) or (nodes and target not in topology.nodes)
            )
            and len(set(nodes)) == len(nodes)
            and all(kind in ("mikrotik_chr", "linux") for kind in kinds.values())
            and all(any(end.node == node for end in own) for node in nodes),
            "The saved power-loss nodes do not match the test",
        )
        _need(
            set(peers)
            == {end for end in far if topology.node(end.node).kind == "mikrotik_chr"}
            and all(re.fullmatch(r"nic[1-9]\d*", nic) for nic in peers.values()),
            "The saved peer NICs do not cover the RouterOS neighbours",
        )
        _need(
            all(
                set(e["status"]) == set(guests)
                for e in (start, stopped, dispatch, powered)
            )
            and all(
                _status(start["status"][node], running=True)
                and _status(stopped["status"][node], running=False)
                and _status(dispatch["status"][node], running=False)
                and _status(powered["status"][node], running=True)
                and _command(stopped["stop"][node], "stop", {})
                and _command(powered["system_reset"][node], "system_reset", {})
                and _command(powered["cont"][node], "cont", {})
                for node in guests
            ),
            "The captured monitor replies do not show a paused guest followed by its reset",
        )
        _need(
            _carrier(start, own, far, peers, up=True)
            and _carrier(stopped, own, far, peers, up=False)
            and _carrier(powered, own, far, peers, up=True)
            and all(
                set(e["facing"]) == {str(p) for p in peers}
                and all(
                    _command(e["facing"][str(p)], "set_link", {"name": nic, "up": up})
                    for p, nic in peers.items()
                )
                for e, up in ((stopped, False), (powered, True))
            ),
            "The saved carrier reads do not show every data cable down and back up",
        )
        held = (dispatch["mono_ns"] - stopped["mono_ns"]) / NS
        _need(
            start["mono_ns"]
            <= stopped["mono_ns"]
            <= dispatch["mono_ns"]
            <= powered["mono_ns"]
            and dispatch["opening"] == opening
            and held >= hold_s,
            "The guest power loss did not hold for the requested interval",
        )
        boots = {}
        for node in guests:
            before = routeros.uptime_ns(start["uptime"][node])
            after, elapsed = lab_reboot.uptime_proof(
                events, before, dispatch, node, closing, "power"
            )
            boots[node] = before, after, elapsed
        healthy = lab_reboot.health_proof(
            folder, events, target, closing, items, "power"
        )
        recovered = (healthy["mono_ns"] - dispatch["mono_ns"]) / NS
        _need(
            all(
                powered["mono_ns"]
                <= dispatch["mono_ns"] + elapsed
                <= healthy["mono_ns"]
                for _, _, elapsed in boots.values()
            )
            and healthy["verdict"] == "pass"
            and recovered <= wait_s,
            "The recorded new boot and lab state did not recover within the deadline",
        )
        ports = [str(end) for end in own]
        if nodes == (target,) and guests == [target]:
            before, after, elapsed = boots[target]
            result.update(
                verdict="pass",
                ports=ports,
                held_s=held,
                before_uptime_s=before / NS,
                after_uptime_s=after / NS,
                elapsed_s=elapsed / NS,
                healthy_s=recovered,
            )
        else:
            result.update(
                verdict="pass",
                nodes=list(nodes),
                ports=ports,
                held_s=held,
                boots={
                    node: {
                        "before_uptime_s": before / NS,
                        "after_uptime_s": after / NS,
                        "elapsed_s": elapsed / NS,
                    }
                    for node, (before, after, elapsed) in boots.items()
                },
                healthy_s=recovered,
            )
    except (
        OSError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        lab.LabError,
        intent.IntentError,
    ) as error:
        result["reason"] = str(error)
    return result
