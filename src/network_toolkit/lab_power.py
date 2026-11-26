# SPDX-License-Identifier: MIT
"""Abrupt guest power loss and recovery on a containerlab RouterOS switch."""

from __future__ import annotations

import ipaddress
import json
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from network_toolkit import intent, lab, lab_reboot
from network_toolkit.platforms.mikrotik_routeros import intent as routeros
from network_toolkit.traffic import NS

if TYPE_CHECKING:
    from network_toolkit.client import NetworkaClient


@dataclass(frozen=True)
class Power:
    switch: str
    on: bool


@dataclass(frozen=True)
class Layout:
    own: tuple[lab.Point, ...]
    far: tuple[lab.Point, ...]
    guest: lab.Qemu
    peers: Mapping[lab.Point, lab.Qemu]


@dataclass
class Outage:
    layout: Layout
    opening: int
    before_ns: int
    links: set[lab.Point] = field(default_factory=set)
    nics: set[lab.Point] = field(default_factory=set)
    reset_pending: bool = False
    resume_pending: bool = False


def ends(topology: lab.Lab, switch: str) -> tuple[tuple[lab.Point, lab.Point], ...]:
    return tuple(
        (end, peer)
        for left, right in topology.links
        for end, peer in ((left, right), (right, left))
        if end.node == switch
    )


def _need(ok: object, message: str) -> None:
    if not ok:
        raise lab.LabError(message)


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


def layout(topology: lab.Lab, switch: str) -> Layout:
    """Discover all data links from the deployed topology and guest NIC layout."""
    links = ends(topology, switch)
    _need(links, f"{switch} has no data cables in the lab")
    own, far = zip(*links, strict=True)
    nics = [_nic(topology, end) for end in own]
    _need(
        len({(nic.pid, nic.qmp_host, nic.qmp_port) for nic in nics}) == 1,
        f"{switch} does not have one guest behind all its data cables",
    )
    peers = {}
    for end in far:
        kind = topology.node(end.node).kind
        if kind == "mikrotik_chr":
            peers[end] = _nic(topology, end)
        else:
            _need(kind == "linux", f"{end} is not a supported power-loss neighbour")
    return Layout(own, far, nics[0], peers)


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


class PowerActions:
    """Stop and reset a guest, preserving its container, management and links."""

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

    def __exit__(self, *exc: object) -> None:
        errors = []
        for switch, outage in list(self.active.items()):
            try:
                self.restore(outage)
                self.session.mark("power_cleanup", switch=switch)
            except lab.LabError as error:
                errors.append(f"{switch} power cleanup: {error}")
        if errors:
            msg = "; ".join(errors)
            raise lab.LabError(msg)

    def _link(self, end: lab.Point, *, up: bool) -> None:
        state = "up" if up else "down"
        self.session.lab.run(end.node, "ip", "link", "set", "dev", end.interface, state)

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

    def off(self, switch: str, number: int) -> None:
        plan = self.layouts[switch]
        before = routeros.collect_uptime(self.client, switch, **self.options)
        before_ns = routeros.uptime_ns(before)
        _need(
            before_ns > 0, f"Cannot prove a lower uptime after power loss of {switch}"
        )
        status = lab.qmp_command(plan.guest, "query-status", {})
        _need(_status(status, running=True), f"{switch} is not running")
        baseline = self._observe(plan, up=True)
        active = Outage(plan, number, before_ns)
        self.active[switch] = active
        self.session.mark(
            "power_off_start",
            switch=switch,
            number=number,
            uptime=before,
            peers={str(end): nic.nic for end, nic in plan.peers.items()},
            status=status,
            **baseline,
        )
        active.reset_pending = active.resume_pending = True
        stop = lab.qmp_command(plan.guest, "stop", {})
        for end in plan.own:
            # The command may succeed before an interrupt or a transport error reaches us.
            active.links.add(end)
            self._link(end, up=False)
        facing = {}
        for end, nic in plan.peers.items():
            active.nics.add(end)
            facing[str(end)] = lab.qmp_command(
                nic, "set_link", {"name": nic.nic, "up": False}
            )
        status = lab.qmp_command(plan.guest, "query-status", {})
        _need(_status(status, running=False), f"{switch} did not pause")
        reading = self._observe(plan, up=False)
        self.session.mark(
            "power_off_observed",
            switch=switch,
            number=number,
            stop=stop,
            status=status,
            facing=facing,
            **reading,
        )

    def restore(self, active: Outage) -> dict[str, Any]:
        """Always attempt guest resume and every link, even after one failure."""
        plan = active.layout
        errors = []
        replies: dict[str, Any] = {"facing": {}}
        for attr, command in (
            ("reset_pending", "system_reset"),
            ("resume_pending", "cont"),
        ):
            if not getattr(active, attr):
                continue
            try:
                replies[command] = lab.qmp_command(plan.guest, command, {})
                setattr(active, attr, False)
            except lab.LabError as error:
                errors.append(str(error))
        for end in sorted(active.links):
            try:
                self._link(end, up=True)
                active.links.discard(end)
            except lab.LabError as error:
                errors.append(str(error))
        for end in sorted(active.nics):
            nic = plan.peers[end]
            try:
                replies["facing"][str(end)] = lab.qmp_command(
                    nic, "set_link", {"name": nic.nic, "up": True}
                )
                active.nics.discard(end)
            except lab.LabError as error:
                errors.append(str(error))
        if errors:
            msg = "; ".join(errors)
            raise lab.LabError(msg)
        return replies

    def on(
        self, switch: str, number: int, wait_s: float, items: list[intent.IntentItem]
    ) -> None:
        active = self.active[switch]
        plan = active.layout
        status = lab.qmp_command(plan.guest, "query-status", {})
        _need(_status(status, running=False), f"{switch} did not remain paused")
        dispatch = self.session.mark(
            "power_on_start",
            switch=switch,
            number=number,
            opening=active.opening,
            status=status,
        )
        with lab_reboot._deadline(wait_s):
            replies = self.restore(active)
            status = lab.qmp_command(plan.guest, "query-status", {})
            _need(_status(status, running=True), f"{switch} did not resume")
            reading = self._observe(plan, up=True)
            self.session.mark(
                "power_on_observed",
                switch=switch,
                number=number,
                status=status,
                **replies,
                **reading,
            )
            lab_reboot.wait_uptime(
                self.client,
                self.session,
                switch,
                number,
                active.before_ns,
                dispatch,
                self.options,
                "power",
            )
            lab_reboot.wait_healthy(
                self.client, self.session, switch, number, items, self.options, "power"
            )
        del self.active[switch]


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


def proof(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    switch: str,
    opening: int,
    closing: int,
    hold_s: float,
    wait_s: float,
    items: list[intent.IntentItem],
) -> dict[str, Any]:
    """Prove the guest pause, loss of carrier, reset, new uptime and healthy lab."""
    result: dict[str, Any] = {"switch": switch, "verdict": "error", "limit_s": wait_s}
    try:
        start = _event(events, "power_off_start", switch, opening)
        stopped = _event(events, "power_off_observed", switch, opening)
        dispatch = _event(events, "power_on_start", switch, closing)
        powered = _event(events, "power_on_observed", switch, closing)
        topology = lab.parse_topology(
            json.loads((folder / lab.TOPOLOGY_DATA).read_text())
        )
        own, far = zip(*ends(topology, switch), strict=True)
        peers = {lab.point(p): nic for p, nic in start["peers"].items()}
        _need(
            topology.node(switch).kind == "mikrotik_chr"
            and set(peers)
            == {end for end in far if topology.node(end.node).kind == "mikrotik_chr"}
            and all(re.fullmatch(r"nic[1-9]\d*", nic) for nic in peers.values()),
            "The saved peer NICs do not cover the RouterOS neighbours",
        )
        _need(
            _status(start["status"], running=True)
            and _status(stopped["status"], running=False)
            and _status(dispatch["status"], running=False)
            and _status(powered["status"], running=True)
            and _command(stopped["stop"], "stop", {})
            and _command(powered["system_reset"], "system_reset", {})
            and _command(powered["cont"], "cont", {}),
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
        before = routeros.uptime_ns(start["uptime"])
        after, elapsed = lab_reboot.uptime_proof(
            events, before, dispatch, switch, closing, "power"
        )
        healthy = lab_reboot.health_proof(
            folder, events, switch, closing, items, "power"
        )
        recovered = (healthy["mono_ns"] - dispatch["mono_ns"]) / NS
        _need(
            powered["mono_ns"] <= dispatch["mono_ns"] + elapsed <= healthy["mono_ns"]
            and healthy["verdict"] == "pass"
            and recovered <= wait_s,
            "The recorded new boot and lab state did not recover within the deadline",
        )
        result.update(
            verdict="pass",
            ports=[str(end) for end in own],
            held_s=held,
            before_uptime_s=before / NS,
            after_uptime_s=after / NS,
            elapsed_s=elapsed / NS,
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
