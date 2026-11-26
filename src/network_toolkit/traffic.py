# SPDX-License-Identifier: MIT
"""Outage measurement for numbered ping streams from packet captures.

A capture point is written as `node:interface` and has one pcap. A stream is a
numbered ping whose ICMP identifier is the stream ID. Its source capture point
sees the requests leave and the replies return. Its destination capture point
sees the requests arrive and the replies leave.

A probe is delivered when the request and the reply appear at both capture
points and the reply leaves within 0.5 s of the request. A run of probes that
were not delivered is a gap. Its lower bound is the time between the first and
the last lost request. Its upper bound is the time between the last delivered
request before the gap and the first delivered request after it. A gap belongs
to the window in which its first lost request was sent.

The rules are the ones of the MikroTik MLAG test suite, whose live attempts
replay to the same numbers.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import os
import re
import subprocess
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

NS = 1_000_000_000
# How far a stream may fall behind its interval between two sends and still count as steady.
# A stall of the lab host lasts a fixed time, whatever the interval, so the allowance is fixed too.
SEND_STALL_NS = 350_000_000
# A reply later than this after its request counts as lost.
LATE_REPLY_NS = 500_000_000
REQUEST, REPLY = 8, 0
CACHE = Path.home() / ".cache" / "networka" / "tshark"
FIELDS = ("frame.time_epoch", "icmp.ident", "icmp.type", "icmp.seq")

# (ICMP identifier, ICMP type, sequence) to the epoch time in ns of each sighting.
Frames = dict[tuple[int, int, int], list[int]]


@dataclass(frozen=True, slots=True)
class Stream:
    """One numbered ping stream between two capture points, sent every `interval_s`."""

    id: int
    source: str
    destination: str
    interval_s: float


@dataclass(frozen=True, slots=True)
class Window:
    """One step of a test, from its start to its end in epoch ns."""

    name: str
    start_ns: int
    end_ns: int


def seconds(value: int) -> float:
    return round(value / NS, 6)


@functools.cache
def tshark_version() -> str:
    return subprocess.check_output(
        ["tshark", "--version"],  # noqa: S607
        text=True,
        timeout=25,
    ).splitlines()[0]


def tshark_fields(pcap: Path, args: Sequence[str]) -> str:
    """TShark field output, cached under the pcap's SHA-256 and the query."""
    digest = sha256(pcap)
    query = hashlib.sha256("\0".join((tshark_version(), *args)).encode()).hexdigest()
    cached = CACHE / digest[:2] / f"{digest}-{query[:16]}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    output = subprocess.check_output(
        ["tshark", "-n", "-r", str(pcap), *args],  # noqa: S607
        text=True,
        stderr=subprocess.PIPE,
        timeout=25,
    )
    cached.parent.mkdir(parents=True, exist_ok=True)
    partial = cached.with_name(f"{cached.name}.{os.getpid()}")
    partial.write_text(output, encoding="utf-8")
    partial.replace(cached)
    return output


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def decode(pcap: Path) -> Frames:
    """Every echo request and reply in one capture, in capture order."""
    args = ["-Y", "icmp", "-T", "fields", "-E", "occurrence=f"]
    for name in FIELDS:
        args.extend(("-e", name))
    frames: Frames = defaultdict(list)
    for line in tshark_fields(pcap, args).splitlines():
        stamp, ident, kind, seq = line.split("\t")
        if ident and kind in ("0", "8"):
            frames[int(ident), int(kind), int(seq)].append(int(Decimal(stamp) * NS))
    return frames


def check_capture(pcap: Path, log: Path | None = None) -> dict[str, Any]:
    """Whether a capture is usable: the file exists and the kernel dropped nothing.

    `kernel_dropped` comes from the tcpdump log and is None without one.
    """
    present = pcap.is_file()
    dropped = None
    if log is not None and log.is_file():
        match = re.search(r"^(\d+) packets dropped by kernel$", log.read_text(), re.M)
        dropped = int(match[1]) if match else None
    return {
        "path": str(pcap),
        "present": present,
        "sha256": sha256(pcap) if present else None,
        "kernel_dropped": dropped,
        "valid": present and (log is None or dropped == 0),
    }


def measure(
    captures: Mapping[str, Path],
    streams: Sequence[Stream],
    windows: Sequence[Window],
) -> dict[str, Any]:
    """Decode the captures that the streams use and measure every stream."""
    points = {point for s in streams for point in (s.source, s.destination)}
    missing = sorted(points - captures.keys())
    if missing:
        msg = f"No capture for {', '.join(missing)}"
        raise ValueError(msg)
    return measure_frames(
        {point: decode(captures[point]) for point in sorted(points)},
        streams,
        windows,
    )


def _window_of(stamp: int, windows: Sequence[Window]) -> str | None:
    return next((w.name for w in windows if w.start_ns <= stamp < w.end_ns), None)


def measure_frames(
    frames: Mapping[str, Frames],
    streams: Sequence[Stream],
    windows: Sequence[Window],
) -> dict[str, Any]:
    """Measure every stream from decoded frames.

    Only requests sent from the start of the first window to the end of the
    last window count. Times in the result are seconds from that start.
    """
    start, end = windows[0].start_ns, windows[-1].end_ns
    result: dict[str, Any] = {
        "start_ns": start,
        "end_ns": end,
        "streams": {},
        "windows": {
            w.name: {
                "start_s": seconds(w.start_ns - start),
                "end_s": seconds(w.end_ns - start),
                "streams": {},
            }
            for w in windows
        },
    }
    for stream in streams:
        flow, sends, good = _stream(
            stream, frames[stream.source], frames[stream.destination], windows
        )
        result["streams"][str(stream.id)] = flow
        lost, duplicates = set(flow["lost"]), set(flow["duplicates"])
        gaps = flow["gaps"]
        for w in windows:
            inside = {
                seq for seq, stamp in sends.items() if w.start_ns <= stamp < w.end_ns
            }
            own = [gap for gap in gaps if gap["window"] == w.name]
            result["windows"][w.name]["streams"][str(stream.id)] = {
                "sent": len(inside),
                "delivered": len(inside & good),
                "lost": len(inside & lost),
                "duplicates": len(inside & duplicates),
                "outage": _outage(own),
            }
    return result


def _stream(
    stream: Stream, sent: Frames, received: Frames, windows: Sequence[Window]
) -> tuple[dict[str, Any], dict[int, int], set[int]]:
    """Match requests and replies of one stream at both ends and find its gaps."""
    ident = stream.id
    start, end = windows[0].start_ns, windows[-1].end_ns
    sends = {
        seq: stamps[0]
        for (i, kind, seq), stamps in sent.items()
        if i == ident and kind == REQUEST and start <= stamps[0] < end
    }
    seen = sorted(sends)
    bad: dict[int, str] = {}
    good: set[int] = set()
    duplicates = []
    mismatches = []
    for seq in seen:
        outbound, reply = (ident, REQUEST, seq), (ident, REPLY, seq)
        if len(sent.get(reply, [])) > 1 or len(received.get(outbound, [])) > 1:
            duplicates.append(seq)
        if reply in sent and (outbound not in received or reply not in received):
            mismatches.append(seq)
        if outbound not in received:
            bad[seq] = "request absent at destination"
        elif reply not in received:
            bad[seq] = "reply absent at destination"
        elif reply not in sent:
            bad[seq] = "reply absent at source"
        elif sent[reply][0] - sends[seq] > LATE_REPLY_NS:
            bad[seq] = "late reply"
        else:
            good.add(seq)
    gaps = []
    if seen:
        n = seen[0]
        while n <= seen[-1]:
            if n in good:
                n += 1
                continue
            first = n
            while n <= seen[-1] and n not in good:
                n += 1
            missing = [seq for seq in range(first, n) if seq in sends]
            prev, nxt = sends.get(first - 1), sends.get(n)
            lower = sends[missing[-1]] - sends[missing[0]] if missing else 0
            upper = nxt - prev if prev is not None and nxt is not None else None
            if missing:
                begins = sends[missing[0]]
            else:
                begins = prev if prev is not None else start
            gaps.append(
                {
                    "first_seq": first,
                    "last_seq": n - 1,
                    "lost": len(missing),
                    "absent_at_source": n - first - len(missing),
                    "lower_s": seconds(lower),
                    "upper_s": seconds(upper) if upper is not None else None,
                    "begins_s": seconds(begins - start),
                    "window": _window_of(begins, windows),
                    "where": sorted({bad[seq] for seq in missing}),
                }
            )
    ordered = [start, *sorted(sends.values()), end]
    max_interval = max(b - a for a, b in itertools.pairwise(ordered))
    gap_limit = round(stream.interval_s * NS) + SEND_STALL_NS
    by_time = sorted((stamp, seq) for seq, stamp in sends.items())
    bounds: list[tuple[int, int | None]] = [(start, None), *by_time, (end, None)]
    pauses = [
        {
            "from_s": seconds(a - start),
            "to_s": seconds(b - start),
            "gap_s": seconds(b - a),
            "after_seq": before,
            "before_seq": after,
        }
        for (a, before), (b, after) in itertools.pairwise(bounds)
        if b - a > gap_limit
    ]
    flow = {
        "source": stream.source,
        "destination": stream.destination,
        "interval_s": stream.interval_s,
        "sent": len(sends),
        "delivered": len(good),
        "lost": sorted(bad),
        "duplicates": duplicates,
        "capture_mismatches": mismatches,
        "gaps": gaps,
        "max_send_interval_s": seconds(max_interval),
        "send_gap_limit_s": seconds(gap_limit),
        "send_pauses": pauses,
        "cadence_ok": not pauses,
    }
    return flow, sends, good


def _outage(gaps: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The longest outage of the gaps, as the MLAG suite reports it per phase."""
    if not gaps:
        return None
    uppers = [gap["upper_s"] for gap in gaps]
    return {
        "lower_s": max(gap["lower_s"] for gap in gaps),
        "upper_s": None if None in uppers else max(uppers),
        "lost": sum(gap["lost"] for gap in gaps),
    }


def baseline(
    result: dict[str, Any], window: str, minimum: Mapping[str, int]
) -> dict[str, Any]:
    """Pass when every stream delivered at least its `minimum` probes and lost none.

    A duplicated reply also fails the baseline.
    """
    streams = {
        ident: {
            "delivered": counts["delivered"],
            "min_delivered": minimum[ident],
            "lost": counts["lost"],
            "duplicates": counts["duplicates"],
            "ok": counts["delivered"] >= minimum[ident]
            and not counts["lost"]
            and not counts["duplicates"],
        }
        for ident, counts in result["windows"][window]["streams"].items()
    }
    verdict: Literal["pass", "fail"] = (
        "pass" if all(s["ok"] for s in streams.values()) else "fail"
    )
    return {"window": window, "verdict": verdict, "streams": streams}
