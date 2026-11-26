# SPDX-License-Identifier: MIT
"""Outage measurement for ping streams from packet captures.

A capture point is written as `node:interface` and has one pcap. A stream is a
steady series of pings from one capture point to another, and its ICMP
identifier tells streams apart. A ping's sequence and echoed payload identify
each attempt. Its source capture point sees the requests leave and the replies
return. Its destination capture point sees the requests arrive and the replies
leave.

A ping is delivered when the request and the reply appear at both capture
points and the reply returns within 0.5 s of the request. A run of pings that
were not delivered is an outage. Its lower bound is the time between the first and
the last lost request. Its upper bound is the time between the last delivered
request before the outage and the first delivered request after it. An outage counts
in every window it overlaps, with its outage and its lost pings alike.
"""

from __future__ import annotations

import itertools
import re
import subprocess
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

NS = 1_000_000_000
# One ping every 100 ms resolves an outage to 0.1 s, ten times finer than a 1 s limit.
INTERVAL_NS = 100_000_000
# A healthy lab path answers within milliseconds, so a reply after 500 ms counts as lost.
LATE_REPLY_NS = 500_000_000
# Leave half a ping interval below the late-reply deadline so a sender pause cannot hide it.
SEND_GAP_LIMIT_NS = LATE_REPLY_NS - INTERVAL_NS // 2
# A test's small pcaps decode within seconds, so a minute only stops a hung tshark.
TSHARK_TIMEOUT_S = 60
REQUEST, REPLY = 8, 0
FIELDS = ("frame.time_epoch", "icmp.ident", "icmp.type", "icmp.seq", "@icmp")
ICMP_HEADER_LENGTH = 8
ICMP_SEQUENCE_MODULUS = 1 << 16

# (ICMP identifier, ICMP type, probe) to the epoch time in ns of each sighting.
Probe = tuple[int, bytes]  # Sequence and payload, which includes the send timestamp.
Frames = dict[tuple[int, int, Probe], list[int]]


@dataclass(frozen=True, slots=True)
class Stream:
    """One ping stream between two capture points, told apart by its ICMP identifier."""

    name: str
    ident: int
    source: str
    destination: str


@dataclass(frozen=True, slots=True)
class Window:
    """One part of a test, from its start to its end in epoch ns."""

    name: str
    start_ns: int
    end_ns: int


def seconds(value: int) -> float:
    return round(value / NS, 6)


def lost_text(lost: int, lower_s: float | None, upper_s: float | None) -> str:
    """A count of lost pings with the interval and the time it stands for."""
    every = f"at one ping every {INTERVAL_NS // 1_000_000} ms"
    if lower_s is None:
        return f"0 pings lost {every}, traffic stopped for 0 s"
    count = f"{lost} ping{'' if lost == 1 else 's'} lost {every}"
    if upper_s is None:
        return f"{count}, traffic stopped for at least {round(lower_s, 3):g} s"
    return (
        f"{count}, traffic stopped for {round(lower_s, 3):g} to {round(upper_s, 3):g} s"
    )


def decode(pcap: Path) -> Frames:
    """Every echo request and reply in one capture, in capture order."""
    args = ["tshark", "-n", "-r", str(pcap), "-Y", "icmp", "-T", "fields"]
    args += ["-E", "occurrence=f"]
    for name in FIELDS:
        args.extend(("-e", name))
    done = subprocess.run(
        args, capture_output=True, text=True, timeout=TSHARK_TIMEOUT_S, check=False
    )
    # A capture still being written can end in half a packet; tshark says so and decodes the rest.
    if done.returncode and "cut short in the middle of a packet" not in done.stderr:
        raise subprocess.CalledProcessError(
            done.returncode, args, done.stdout, done.stderr
        )
    frames: Frames = defaultdict(list)
    for line in done.stdout.splitlines():
        stamp, ident, kind, seq, raw = line.split("\t")
        if ident and kind in ("0", "8"):
            # iputils can retry a sequence after a send error with a new timestamp.
            # The echo preserves these bytes, including on hosts with different clocks.
            payload = bytes.fromhex(raw.replace(":", ""))[ICMP_HEADER_LENGTH:]
            frames[int(ident), int(kind), (int(seq), payload)].append(
                int(Decimal(stamp) * NS)
            )
    return frames


def kernel_drops(log: str) -> int | None:
    """The kernel drop count that tcpdump prints when it stops, or None."""
    found = re.search(r"^(\d+) packets? dropped by kernel$", log, re.MULTILINE)
    return int(found.group(1)) if found else None


def check_capture(pcap: Path, log: Path) -> dict[str, Any]:
    """Whether a capture is usable: the pcap exists and the kernel dropped nothing."""
    present = pcap.is_file()
    dropped = kernel_drops(log.read_text(errors="replace")) if log.is_file() else None
    return {
        "present": present,
        "kernel_dropped": dropped,
        "valid": present and dropped == 0,
    }


def first_reply(frames: Frames, ident: int) -> int | None:
    """The epoch ns of the first reply of a stream at its source, or None."""
    stamps = [
        s[0] for (i, kind, _), s in frames.items() if i == ident and kind == REPLY
    ]
    return min(stamps, default=None)


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
        "interval_s": seconds(INTERVAL_NS),
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
        flow, sends, good, duplicates = _stream(
            stream, frames[stream.source], frames[stream.destination], windows
        )
        result["streams"][stream.name] = flow
        for w in windows:
            inside = {
                probe
                for probe, stamp in sends.items()
                if w.start_ns <= stamp < w.end_ns
            }
            own = [gap for gap in flow["gaps"] if w.name in gap["windows"]]
            outage = _outage(own)
            lost = outage["lost"] if outage else 0
            result["windows"][w.name]["streams"][stream.name] = {
                "sent": len(inside),
                "delivered": len(inside & good),
                "lost": lost,
                "duplicates": len(inside & duplicates),
                "outage": outage,
                "summary": lost_text(
                    lost,
                    outage["lower_s"] if outage else None,
                    outage["upper_s"] if outage else None,
                ),
            }
    return result


def _stream(
    stream: Stream, sent: Frames, received: Frames, windows: Sequence[Window]
) -> tuple[dict[str, Any], dict[Probe, int], set[Probe], set[Probe]]:
    """Match requests and replies of one stream at both ends and find its gaps."""
    ident = stream.ident
    start, end = windows[0].start_ns, windows[-1].end_ns
    sends = {
        probe: stamps[0]
        for (i, kind, probe), stamps in sent.items()
        if i == ident and kind == REQUEST and start <= stamps[0] < end
    }
    seen = sorted(sends, key=sends.__getitem__)
    bad: dict[Probe, str] = {}
    good: set[Probe] = set()
    duplicates: set[Probe] = set()
    mismatches = []
    for probe in seen:
        outbound, reply = (ident, REQUEST, probe), (ident, REPLY, probe)
        if len(sent.get(reply, [])) > 1 or len(received.get(outbound, [])) > 1:
            duplicates.add(probe)
        if reply in sent and (outbound not in received or reply not in received):
            mismatches.append(probe[0])
        if outbound not in received:
            bad[probe] = "request absent at destination"
        elif reply not in received:
            bad[probe] = "reply absent at destination"
        elif reply not in sent:
            bad[probe] = "reply absent at source"
        elif sent[reply][0] - sends[probe] > LATE_REPLY_NS:
            bad[probe] = "late reply"
        else:
            good.add(probe)
    gaps = _gaps(seen, sends, bad, windows)
    gap_limit = SEND_GAP_LIMIT_NS
    by_time = [(sends[probe], probe[0]) for probe in seen]
    bounds: list[tuple[int, int | None]] = [(start, None), *by_time, (end, None)]
    max_interval = max(b - a for (a, _), (b, _) in itertools.pairwise(bounds))
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
        "ident": ident,
        "source": stream.source,
        "destination": stream.destination,
        "interval_s": seconds(INTERVAL_NS),
        "sent": len(sends),
        "delivered": len(good),
        "lost_seqs": sorted(probe[0] for probe in bad),
        "duplicates": sorted(probe[0] for probe in duplicates),
        "capture_mismatches": mismatches,
        "gaps": gaps,
        "max_send_interval_s": seconds(max_interval),
        "send_gap_limit_s": seconds(gap_limit),
        "send_pauses": pauses,
        "cadence_ok": not pauses,
    }
    return flow, sends, good, duplicates


def _gaps(
    seen: Sequence[Probe],
    sends: Mapping[Probe, int],
    bad: Mapping[Probe, str],
    windows: Sequence[Window],
) -> list[dict[str, Any]]:
    """Locate stops between delivered attempts, leaving slots for unseen sequences."""
    start = windows[0].start_ns
    indexed: dict[int, Probe] = {}
    position = 0
    previous_seq = seen[0][0] if seen else 0
    for probe in seen:
        seq = probe[0]
        position += max(1, (seq - previous_seq) % ICMP_SEQUENCE_MODULUS)
        indexed[position] = probe
        previous_seq = seq
    delivered = [slot for slot, probe in indexed.items() if probe not in bad]
    gaps = []
    for previous, next_delivered in itertools.pairwise([0, *delivered, position + 1]):
        first, last = previous + 1, next_delivered - 1
        if first > last:
            continue
        lost = [indexed[slot] for slot in range(first, last + 1) if slot in indexed]
        before, after = indexed.get(previous), indexed.get(next_delivered)
        prev = sends[before] if before is not None else None
        nxt = sends[after] if after is not None else None
        lower = sends[lost[-1]] - sends[lost[0]] if lost else 0
        upper = nxt - prev if prev is not None and nxt is not None else None
        if lost:
            begins, ends = sends[lost[0]], sends[lost[-1]]
        else:
            begins = ends = prev if prev is not None else start
        upper_s = seconds(upper) if upper is not None else None
        first_seq = indexed[first][0] if first in indexed else indexed[previous][0] + 1
        last_seq = (
            indexed[last][0] if last in indexed else indexed[next_delivered][0] - 1
        )
        gaps.append(
            {
                "first_seq": first_seq % ICMP_SEQUENCE_MODULUS,
                "last_seq": last_seq % ICMP_SEQUENCE_MODULUS,
                "lost": len(lost),
                "absent_at_source": last - first + 1 - len(lost),
                "lower_s": seconds(lower),
                "upper_s": upper_s,
                "summary": lost_text(len(lost), seconds(lower), upper_s),
                "begins_s": seconds(begins - start),
                "ends_s": seconds(ends - start),
                "windows": [
                    w.name for w in windows if begins < w.end_ns and ends >= w.start_ns
                ],
                "where": sorted({bad[probe] for probe in lost}),
            }
        )
    return gaps


def _outage(gaps: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The longest outage of the gaps and the pings they lost."""
    if not gaps:
        return None
    uppers = [gap["upper_s"] for gap in gaps]
    return {
        "lower_s": max(gap["lower_s"] for gap in gaps),
        "upper_s": None if None in uppers else max(uppers),
        "lost": sum(gap["lost"] for gap in gaps),
    }


def quiet(result: Mapping[str, Any], window: str) -> dict[str, Any]:
    """The quiet window rule: no lost and no duplicate ping, and enough delivered.

    Allow a 10 percent longer send interval on a busy host, and subtract one
    ping because the window edges can cut a ping interval.
    """
    measured = result["windows"][window]
    length_ns = round((measured["end_s"] - measured["start_s"]) * NS)
    minimum = length_ns // (INTERVAL_NS * 11 // 10) - 1
    streams = {
        name: {
            "delivered": counts["delivered"],
            "min_delivered": minimum,
            "lost": counts["lost"],
            "duplicates": counts["duplicates"],
            "summary": counts["summary"],
            "ok": counts["delivered"] >= minimum
            and not counts["outage"]
            and not counts["duplicates"],
        }
        for name, counts in measured["streams"].items()
    }
    return {
        "window": window,
        "start_s": measured["start_s"],
        "end_s": measured["end_s"],
        "verdict": "pass" if all(s["ok"] for s in streams.values()) else "fail",
        "streams": streams,
    }


def quiet_problems(verdict: Mapping[str, Any]) -> list[str]:
    """One sentence per stream that breaks the quiet window rule."""
    return [
        f"{name} delivered {s['delivered']} of at least {s['min_delivered']} pings, "
        f"{s['summary']}, {s['duplicates']} duplicated"
        for name, s in verdict["streams"].items()
        if not s["ok"]
    ]
