# SPDX-License-Identifier: MIT
"""Typed traffic faults and their namespace and replay evidence."""

from __future__ import annotations

import re
import shlex
import statistics
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from network_toolkit import intent, lab, lab_reboot, traffic
from network_toolkit.platforms.linux import intent as linux

if TYPE_CHECKING:
    from network_toolkit.client import NetworkaClient

DROP_COUNT = re.compile(r"\(dropped (\d+),")
NETEM_HANDLE = "982:"
# The qualified fast-rate LACP endpoints transmit once per second.
LACP_POLL_S = 0.2
LACP_RECOVERY_S = 30.0


@dataclass(frozen=True)
class Impair:
    point: str
    clear: bool
    direction: str = "out"
    loss_percent: float = 0
    delay_ms: int = 0
    jitter_ms: int = 0
    delay_stream: str | None = None


@dataclass(frozen=True)
class CutPing:
    stream: str
    clear: bool
    point: str = ""


@dataclass(frozen=True)
class SilenceLacp:
    point: str
    clear: bool
    bond: str = ""


TrafficFault = Impair | CutPing | SilenceLacp
FaultKey = tuple[type, str]


def key(fault: TrafficFault) -> FaultKey:
    return type(fault), name(fault)


def name(fault: TrafficFault) -> str:
    return fault.stream if isinstance(fault, CutPing) else fault.point


def parameters(fault: TrafficFault) -> dict[str, Any]:
    return {key: value for key, value in asdict(fault).items() if value is not None}


def tc_rule(
    fault: CutPing | SilenceLacp, addresses: tuple[str, str]
) -> tuple[str, list[str]]:
    if isinstance(fault, CutPing):
        source, target = addresses
        return "ingress", [
            "protocol",
            "ip",
            "pref",
            "43",
            "flower",
            "src_ip",
            source,
            "dst_ip",
            target,
            "ip_proto",
            "icmp",
            "type",
            "8",
            "action",
            "drop",
        ]
    return "egress", [
        "protocol",
        "0x8809",
        "pref",
        "43",
        "flower",
        "dst_mac",
        "01:80:c2:00:00:02",
        "action",
        "drop",
    ]


def netem_args(fault: Impair) -> list[str]:
    args = []
    if fault.delay_ms:
        args += ["delay", f"{fault.delay_ms}ms"]
    if fault.jitter_ms:
        args.append(f"{fault.jitter_ms}ms")
    if fault.loss_percent:
        args += ["loss", f"{fault.loss_percent:g}%"]
    return args


def _root(text: str) -> list[str]:
    [root] = [
        line.split()
        for line in text.splitlines()
        if line.startswith("qdisc ") and "root" in line.split()
    ]
    return root


def _milliseconds(text: str) -> float:
    match = re.fullmatch(r"([\d.]+)(us|ms|s)", text)
    if match is None:
        msg = f"invalid tc duration {text!r}"
        raise ValueError(msg)
    value, units = match.groups()
    return float(value) * {"us": 0.001, "ms": 1, "s": 1000}[units]


def _netem_matches(raw: str, fault: Impair) -> bool:
    root = _root(raw)
    if root[1] != "netem":
        return False
    delay = jitter = loss = 0.0
    if "delay" in root:
        first = root.index("delay") + 1
        delay = _milliseconds(root[first])
        if first + 1 < len(root) and re.fullmatch(
            r"[\d.]+(?:us|ms|s)", root[first + 1]
        ):
            jitter = _milliseconds(root[first + 1])
    if "loss" in root:
        loss = float(root[root.index("loss") + 1].removesuffix("%"))
    # tc rounds its probability display. YAML uses no more than two decimal places.
    return (
        delay == fault.delay_ms
        and jitter == fault.jitter_ms
        and abs(loss - fault.loss_percent) < 0.005
    )


def _drop_count(raw: str) -> int:
    counts = DROP_COUNT.findall(raw)
    return sum(int(count) for count in counts)


def _has_classifier(raw: str) -> bool:
    return any(
        line.startswith(("qdisc clsact ", "qdisc ingress "))
        for line in raw.splitlines()
    )


def _filter_matches(
    raw: str, fault: CutPing | SilenceLacp, addresses: tuple[str, str]
) -> bool:
    if "pref 43 flower" not in raw or "action drop" not in raw:
        return False
    lines = {line.strip() for line in raw.splitlines()}
    if isinstance(fault, SilenceLacp):
        return {"eth_type 8809", "dst_mac 01:80:c2:00:00:02"} <= lines
    source, target = addresses
    return {
        "eth_type ipv4",
        "ip_proto icmp",
        "icmp_type 8",
        f"src_ip {source}",
        f"dst_ip {target}",
    } <= lines


def _qdisc(topology: lab.Lab, end: lab.Point) -> str:
    return topology.run(end.node, "tc", "-s", "qdisc", "show", "dev", end.interface)


def _filter_stats(topology: lab.Lab, end: lab.Point, direction: str) -> str:
    return topology.run(
        end.node, "tc", "-s", "filter", "show", "dev", end.interface, direction
    )


def _classifier_add(
    topology: lab.Lab, end: lab.Point, direction: str, rule: Sequence[str]
) -> None:
    """Install after preflight and registering ownership of the interface."""
    topology.run(end.node, "tc", "qdisc", "add", "dev", end.interface, "clsact")
    topology.run(
        end.node, "tc", "filter", "add", "dev", end.interface, direction, *rule
    )


def _classifier_remove(topology: lab.Lab, end: lab.Point, raw: str) -> None:
    """Remove an owned clsact, including a partially installed rule."""
    if any(line.startswith("qdisc clsact ") for line in raw.splitlines()):
        topology.run(end.node, "tc", "qdisc", "del", "dev", end.interface, "clsact")


def _require(ok: object, message: str) -> None:
    if not ok:
        raise lab.LabError(message)


@dataclass
class Installed:
    fault: TrafficFault
    points: tuple[lab.Point, ...]
    addresses: tuple[str, str]
    owned: set[lab.Point]
    baseline: dict[str, str]
    opening: int


class TrafficActions:
    """Own only the qdiscs this run installs, including partial installations."""

    def __init__(self, session: lab.Session) -> None:
        self.session = session
        self.topology = session.lab
        self.installed: dict[FaultKey, Installed] = {}

    def __enter__(self) -> TrafficActions:
        return self

    def __exit__(
        self, _kind: object, original: BaseException | None, _traceback: object
    ) -> None:
        errors = []
        for active in reversed(list(self.installed.values())):
            try:
                restored = self.remove(active)
                _require(
                    _restored(active, restored),
                    f"{name(active.fault)} cleanup did not restore its qdisc",
                )
                self.session.mark("fault_cleanup", target=name(active.fault))
            except Exception as error:
                errors.append(f"{name(active.fault)} fault cleanup: {error}")
        self.session.record_restore_errors(errors, original)

    def tc(self, end: lab.Point, *command: str) -> str:
        return self.topology.run(end.node, "tc", *command)

    def counters(self, active: Installed) -> dict[str, str]:
        if isinstance(active.fault, Impair):
            return {str(end): _qdisc(self.topology, end) for end in active.points}
        direction, _ = tc_rule(active.fault, active.addresses)
        return {
            str(end): _filter_stats(self.topology, end, direction)
            for end in active.points
        }

    def bond(self, fault: SilenceLacp) -> dict[str, intent.Reply]:
        end = lab.point(fault.point)
        return {
            command: {
                "command": command,
                "output": self.topology.run(end.node, *shlex.split(command)),
                "error": None,
            }
            for command in (linux.bond_link(fault.bond), linux.bond_slaves(fault.bond))
        }

    def install(
        self, fault: TrafficFault, number: int, addresses: tuple[str, str]
    ) -> None:
        end = lab.point(fault.point)
        peer = self.topology.peer(end)
        points: tuple[lab.Point, ...] = (end,)
        if isinstance(fault, Impair):
            points = {"out": (end,), "in": (peer,), "both": (end, peer)}[
                fault.direction
            ]
        bond = self.bond(fault) if isinstance(fault, SilenceLacp) else None
        if isinstance(fault, SilenceLacp):
            _require(
                all(self.topology.node(p.node).kind == "linux" for p in points)
                and bond is not None
                and _member(fault, bond, eligible=True),
                f"{fault.point} must start eligible in its Linux LACP bond",
            )
        baseline = {str(p): _qdisc(self.topology, p) for p in points}
        for point, raw in baseline.items():
            if isinstance(fault, Impair):
                # Preserve any pre-existing shaper. Containerlab veths use noqueue.
                _require(_root(raw)[1] == "noqueue", f"{point} has a non-default qdisc")
            else:
                _require(not _has_classifier(raw), f"{point} already has a classifier")
        active = Installed(fault, points, addresses, set(), baseline, number)
        self.installed[key(fault)] = active
        self.session.mark(
            "fault_installing",
            number=number,
            target=name(fault),
            fault=parameters(fault),
            points=[str(p) for p in points],
            peer=str(peer),
            addresses=addresses,
            baseline=baseline,
            bond=bond,
        )
        for p in points:
            # A command can apply its change before an interrupt or timeout.
            active.owned.add(p)
            if isinstance(fault, Impair):
                self.tc(
                    p,
                    "qdisc",
                    "add",
                    "dev",
                    p.interface,
                    "root",
                    "handle",
                    NETEM_HANDLE,
                    "netem",
                    *netem_args(fault),
                )
            else:
                direction, rule = tc_rule(fault, addresses)
                _classifier_add(self.topology, p, direction, rule)
        applied = self.counters(active)
        _require(
            _matches(active, applied), f"{name(fault)} did not show the requested rule"
        )
        self.session.mark(
            "fault_installed",
            number=number,
            target=name(fault),
            raw=applied,
        )

    def remove(self, active: Installed) -> dict[str, str]:
        errors = []
        for p in sorted(active.owned):
            try:
                raw = _qdisc(self.topology, p)
                if isinstance(active.fault, Impair):
                    root = _root(raw)
                    if root[1:3] == ["netem", NETEM_HANDLE]:
                        self.tc(
                            p,
                            "qdisc",
                            "del",
                            "dev",
                            p.interface,
                            "root",
                            "handle",
                            NETEM_HANDLE,
                        )
                else:
                    _classifier_remove(self.topology, p, raw)
                active.owned.discard(p)
            except (ValueError, lab.LabError) as error:
                errors.append(str(error))
        if errors:
            msg = "; ".join(errors)
            raise lab.LabError(msg)
        self.installed.pop(key(active.fault), None)
        return {str(p): _qdisc(self.topology, p) for p in active.points}

    def clear(
        self,
        client: NetworkaClient,
        fault: TrafficFault,
        number: int,
        wait_s: float,
        items: list[intent.IntentItem],
        options: Mapping[str, Any],
    ) -> None:
        active = self.installed[key(fault)]
        started = self.session.mark("fault_clearing", number=number, target=name(fault))
        counters = self.counters(active)
        bond = (
            self.bond(active.fault) if isinstance(active.fault, SilenceLacp) else None
        )
        restored = self.remove(active)
        self.session.mark(
            "fault_cleared",
            number=number,
            target=name(fault),
            opening=active.opening,
            counters=counters,
            bond=bond,
            raw=restored,
        )
        _require(
            _restored(active, restored), f"{name(fault)} did not restore its qdisc"
        )
        if isinstance(active.fault, SilenceLacp):
            failed = f"{active.fault.point} did not withdraw from LACP while carrier stayed up"
            _require(
                bond is not None and _member(active.fault, bond, eligible=False), failed
            )
            deadline = started["mono_ns"] / traffic.NS + (wait_s or LACP_RECOVERY_S)
            while True:
                reading = self.bond(active.fault)
                if _member(active.fault, reading, eligible=True):
                    self.session.mark(
                        "fault_lacp_restored", number=number, bond=reading
                    )
                    break
                _require(
                    time.monotonic() < deadline,
                    f"{active.fault.point} did not rejoin LACP",
                )
                time.sleep(LACP_POLL_S)
        if wait_s:
            remaining = wait_s - (time.monotonic_ns() - started["mono_ns"]) / traffic.NS
            _require(remaining > 0, f"{name(fault)} exhausted its recovery deadline")
            with lab_reboot._deadline(remaining, "Fault recovery"):
                lab_reboot.wait_healthy(
                    client, self.session, name(fault), number, items, options, "fault"
                )


def _member(fault: SilenceLacp, evidence: Mapping[str, Any], *, eligible: bool) -> bool:
    outcome = linux.check_bond_member(
        evidence,
        fault.bond,
        lab.point(fault.point).interface,
        {"carrier": True, "eligible": eligible},
    )
    return outcome.verdict == "pass"


def _matches(active: Installed, readings: Mapping[str, str]) -> bool:
    if (
        not isinstance(readings, Mapping)
        or set(readings) != {str(end) for end in active.points}
        or not all(isinstance(reading, str) for reading in readings.values())
    ):
        return False
    fault = active.fault
    if isinstance(fault, Impair):
        return all(_netem_matches(reading, fault) for reading in readings.values())
    return all(
        _filter_matches(reading, fault, active.addresses)
        for reading in readings.values()
    )


def _restored(active: Installed, readings: Mapping[str, str]) -> bool:
    return (
        isinstance(readings, Mapping)
        and set(readings) == set(active.baseline)
        and all(
            isinstance(reading, str)
            and isinstance(active.baseline[point], str)
            and _has_classifier(reading) == _has_classifier(active.baseline[point])
            and _root(reading)[1:3] == _root(active.baseline[point])[1:3]
            for point, reading in readings.items()
        )
    )


def _event(
    events: Sequence[Mapping[str, Any]], name: str, number: int
) -> Mapping[str, Any]:
    matches = [e for e in events if e["name"] == name and e.get("number") == number]
    _require(
        len(matches) == 1,
        f"Expected one {name} for step {number}, found {len(matches)}",
    )
    return matches[0]


def _rtt(
    capture: Path,
    ident: int,
    windows: Sequence[tuple[int, int]],
) -> tuple[list[float], list[int]]:
    """Median request to reply durations from source capture, in milliseconds."""
    frames = traffic.decode(capture)
    samples: list[list[int]] = [[] for _ in windows]
    for (stream, kind, probe), stamps in frames.items():
        if stream != ident or kind != traffic.REQUEST:
            continue
        replies = frames.get((ident, traffic.REPLY, probe), [])
        if len(stamps) != 1 or len(replies) != 1:
            continue
        delay = replies[0] - stamps[0]
        if not 0 <= delay <= traffic.LATE_REPLY_NS:
            continue
        for current, (start, end) in zip(samples, windows, strict=True):
            if start <= stamps[0] and replies[0] < end:
                current.append(delay)
    counts = [len(current) for current in samples]
    # A median needs at least three complete samples in each phase.
    _require(
        min(counts) >= 3,
        f"Too few ping replies to measure delay in each phase: {counts}",
    )
    return [
        statistics.median(current) * 1000 / traffic.NS for current in samples
    ], counts


def _delay_proof(
    result: dict[str, Any],
    fault: Impair,
    events: Sequence[Mapping[str, Any]],
    measured: Mapping[str, Any],
    pcaps: Mapping[str, Path],
    before: Mapping[str, Any],
    applied: Mapping[str, Any],
    clearing: Mapping[str, Any],
    cleared: Mapping[str, Any],
    count: int,
) -> None:
    assert fault.delay_stream is not None
    stream = measured["streams"][fault.delay_stream]
    neighboring = [
        event
        for event in events
        if event["name"] == "fault_installing"
        and isinstance(event.get("fault"), Mapping)
        and (
            event["target"] == name(fault)
            or event["fault"].get("delay_stream") == fault.delay_stream
        )
    ]
    earlier = {
        event["number"] for event in neighboring if event["number"] < before["number"]
    }
    baseline_start = max(
        (
            event["epoch_ns"]
            for event in events
            if event["name"] == "fault_cleared"
            and event.get("opening") in earlier
            and event["number"] < before["number"]
        ),
        default=measured["start_ns"],
    )
    restored_end = min(
        (
            event["epoch_ns"]
            for event in neighboring
            if event["number"] > cleared["number"]
        ),
        default=measured["end_ns"],
    )
    medians, samples = _rtt(
        pcaps[stream["source"]],
        stream["ident"],
        [
            (baseline_start, before["epoch_ns"]),
            (applied["epoch_ns"], clearing["epoch_ns"]),
            (cleared["epoch_ns"], restored_end),
        ],
    )
    baseline, impaired, restored = medians
    increase = impaired - baseline
    result["delay"] = {
        "stream": fault.delay_stream,
        "baseline_ms": round(baseline, 3),
        "impaired_ms": round(impaired, 3),
        "restored_ms": round(restored, 3),
        "increase_ms": round(increase, 3),
        "samples": samples,
    }
    # Allow 1 ms or 10% for scheduling in addition to configured jitter.
    tolerance = max(1, fault.delay_ms * 0.1)
    margin = tolerance + fault.jitter_ms
    _require(
        max(fault.delay_ms / 2, fault.delay_ms - margin)
        <= increase
        <= count * (fault.delay_ms + margin)
        and abs(restored - baseline) <= tolerance,
        f"{fault.delay_stream} did not show the requested delay and recovery "
        f"({baseline:.3f}, {impaired:.3f}, {restored:.3f} ms median RTT)",
    )


def proofs(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    fault: TrafficFault,
    opening: int,
    closing: int,
    wait_s: float,
    items: list[intent.IntentItem],
    measured: Mapping[str, Any],
    hold_s: float,
    pcaps: Mapping[str, Path],
) -> dict[str, Any]:
    """Rebuild one complete fault and removal proof from command reads and captures."""
    result: dict[str, Any] = {"target": name(fault), "verdict": "error"}
    try:
        before = _event(events, "fault_installing", opening)
        applied = _event(events, "fault_installed", opening)
        clearing = _event(events, "fault_clearing", closing)
        cleared = _event(events, "fault_cleared", closing)
        points = tuple(lab.point(p) for p in before["points"])
        active = Installed(
            fault,
            points,
            tuple(before["addresses"]),
            set(),
            before["baseline"],
            opening,
        )
        first = lab.point(fault.point)
        peer = lab.point(before["peer"])
        expected: tuple[lab.Point, ...] = (first,)
        if isinstance(fault, Impair):
            expected = {"out": (first,), "in": (peer,), "both": (first, peer)}[
                fault.direction
            ]
        _require(
            points == expected
            and first != peer
            and before["fault"] == parameters(fault)
            and cleared["opening"] == opening
            and all(
                e["target"] == name(fault) for e in (before, applied, clearing, cleared)
            )
            and set(active.baseline) == {str(point) for point in points}
            and before["mono_ns"]
            <= applied["mono_ns"]
            <= clearing["mono_ns"]
            <= cleared["mono_ns"]
            and set(active.baseline) == set(cleared["raw"]),
            "Fault events do not identify the requested rule and matching removal",
        )
        _require(
            _matches(active, applied["raw"])
            and _matches(active, cleared["counters"])
            and _restored(active, cleared["raw"]),
            "The saved tc reads do not prove installation and restoration",
        )
        result["points"] = before["points"]
        result["held_s"] = (clearing["mono_ns"] - applied["mono_ns"]) / traffic.NS
        _require(
            result["held_s"] >= hold_s, "The requested fault hold was not completed"
        )
        result["dropped"] = {
            point: _drop_count(raw) for point, raw in cleared["counters"].items()
        }
        if not isinstance(fault, Impair) or fault.loss_percent == 100:
            _require(
                any(result["dropped"].values()),
                "The rule did not record a dropped packet",
            )
        if isinstance(fault, SilenceLacp):
            restored = _event(events, "fault_lacp_restored", closing)
            _require(
                _member(fault, before["bond"], eligible=True)
                and _member(fault, cleared["bond"], eligible=False)
                and _member(fault, restored["bond"], eligible=True)
                and cleared["mono_ns"]
                <= restored["mono_ns"]
                <= clearing["mono_ns"]
                + round((wait_s or LACP_RECOVERY_S) * traffic.NS),
                "The captured Linux bond state did not prove withdrawal with carrier and recovery",
            )
        if wait_s:
            recovered = lab_reboot.health_proof(
                folder, events, name(fault), closing, items, "fault"
            )
            _require(
                recovered["verdict"] == "pass"
                and cleared["mono_ns"]
                <= recovered["mono_ns"]
                <= clearing["mono_ns"] + wait_s * traffic.NS,
                "The lab did not recover within the deadline",
            )
            result["healthy_s"] = (
                recovered["mono_ns"] - clearing["mono_ns"]
            ) / traffic.NS
        if isinstance(fault, Impair) and fault.delay_stream:
            _delay_proof(
                result,
                fault,
                events,
                measured,
                pcaps,
                before,
                applied,
                clearing,
                cleared,
                len(points),
            )
        if isinstance(fault, CutPing):
            stream = measured["streams"][fault.stream]
            start = measured["start_ns"]
            low = (before["epoch_ns"] - start) / traffic.NS
            high = (cleared["epoch_ns"] - start) / traffic.NS
            gaps = [
                gap
                for gap in stream["gaps"]
                if gap["begins_s"] <= high and gap["ends_s"] >= low
            ]
            # The first and last missed probes bound the minimum gap. The
            # surrounding successful probes bound its maximum length.
            _require(
                len(gaps) == 1,
                f"Expected one contiguous cut of {fault.stream}, found {len(gaps)}",
            )
            [gap] = gaps
            unbracketed = (
                "The captured one-way ping gap does not bracket the applied cut"
            )
            _require(
                not gap["absent_at_source"] and gap["upper_s"] is not None, unbracketed
            )
            # Probes leave at the sender's own pace, so the tc markers bound
            # each send instead of a nominal interval. Lost probes leave
            # between installing and cleared, and delivered ones outside
            # installed to clearing.
            sends = sorted(
                stamps[0]
                for (ident, kind, _), stamps in traffic.decode(
                    pcaps[stream["source"]]
                ).items()
                if ident == stream["ident"]
                and kind == traffic.REQUEST
                and start <= stamps[0] < measured["end_ns"]
            )
            offsets = [traffic.seconds(send - start) for send in sends]
            begins = offsets.index(gap["begins_s"])
            ends = offsets.index(gap["ends_s"])
            _require(
                begins > 0 and ends + 1 < len(sends),
                "The cut has no delivered ping before or after it in the capture",
            )
            upper_hold = (cleared["mono_ns"] - before["mono_ns"]) / traffic.NS
            _require(
                gap["lower_s"] <= upper_hold
                and result["held_s"] <= gap["upper_s"]
                and sends[begins - 1] <= applied["epoch_ns"]
                and sends[begins] >= before["epoch_ns"]
                and sends[ends] <= cleared["epoch_ns"]
                and sends[ends + 1] >= clearing["epoch_ns"],
                unbracketed,
            )
    except (
        OSError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        subprocess.SubprocessError,
        lab.LabError,
        intent.IntentError,
    ) as error:
        result["reason"] = str(error)
        return result
    result["verdict"] = "pass"
    return result
