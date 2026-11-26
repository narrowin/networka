# SPDX-License-Identifier: MIT
"""Lab tests: a test file, its fixed flow in a containerlab lab, the verdict and replay.

A lab file holds what all tests of one lab share: the state statements, the
ping streams and the file the switch logs arrive in. A test file names its lab
file and holds ordered steps. A step sets one cable down or up, holds for a
time, limits the outage of every stream and can carry log rules. The flow
checks the state, starts captures and streams, checks a quiet window, runs the
steps, checks the state again and stops.

The verdict is computed from the saved evidence only. `replay` therefore
computes the same `result.json` and `timeline.tsv` again without the lab.
"""

from __future__ import annotations

import importlib
import json
import math
import re
import subprocess
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, NoReturn

import yaml

from network_toolkit import intent, lab, traffic
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.intent import IntentItem, Verdict

if TYPE_CHECKING:
    from network_toolkit.client import NetworkaClient

TEST_FILE = "test.yaml"
LAB_FILE = "lab.yaml"
EVENTS_FILE = "events.jsonl"
SYSLOG_FILE = "syslog.log"
RESULT_FILE = "result.json"
TIMELINE_FILE = "timeline.tsv"
NS = traffic.NS
# Three LACP messages at the fast rate of one per second, so a bond still settling loses pings here and not in a step.
QUIET_S = 3.0
# ARP and the first ping take milliseconds, so a stream without a reply after 5 s has no path.
FIRST_REPLY_S = 5.0
# The last pings of a step still get their reply within the late reply limit, plus one interval for the last ping.
SETTLE_S = (traffic.LATE_REPLY_NS + traffic.INTERVAL_NS) / NS
# The two clocks of the lab host drift microseconds apart in a test, so 50 ms means the wall clock was stepped.
CLOCK_LIMIT_NS = 50_000_000
# UDP on the management bridge arrives within milliseconds, so 1 s is ample for the end markers.
MARKER_WAIT_S = 1.0
QUIET = "quiet window"
EVERY = "every"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

TEST_FIELDS = (("name", "purpose", "lab", "steps"), ("source", "log"))
LAB_FIELDS = (("state", "streams"), ("switch_log",))
STREAM_FIELDS = (("name", "from", "to"), ())
STEP_FIELDS = (
    ("name", "cable", "state", "hold_s", "max_outage_s", "expected"),
    ("log",),
)
LOG_FIELDS = ((), ("must", "must_not"))
RULE_FIELDS = (("switch", "text"), ())
STATEMENT_FIELDS = (("statement", "checks"), ("source",))


class LabTestError(NetworkToolkitError):
    """A test file, a lab file or saved evidence cannot be used."""


@dataclass(frozen=True)
class StreamSpec:
    name: str
    ident: int
    source: str
    destination: str


@dataclass(frozen=True)
class Rule:
    """A log rule: `text` must or must not appear in the log of `switch`."""

    kind: str
    switch: str
    text: str


@dataclass(frozen=True)
class Step:
    name: str
    cable: str
    state: str
    hold_s: float
    limits: tuple[tuple[str, float], ...]
    expected: str
    log: tuple[Rule, ...]


@dataclass(frozen=True)
class Statement:
    statement: str
    source: str | None
    checks: tuple[IntentItem, ...]


@dataclass(frozen=True)
class LabTest:
    """A validated test file with its lab file."""

    path: Path
    text: str
    name: str
    purpose: str
    source: str | None
    lab_text: str
    statements: tuple[Statement, ...]
    streams: tuple[StreamSpec, ...]
    switch_log: str | None
    log: tuple[Rule, ...]
    steps: tuple[Step, ...]

    def items(self) -> list[IntentItem]:
        """Every check of every statement, in file order."""
        return [item for s in self.statements for item in s.checks]

    def ends(self) -> set[str]:
        """The capture points at both ends of every stream."""
        return {p for s in self.streams for p in (s.source, s.destination)}


@dataclass(frozen=True)
class LogLine:
    """One line of the switch log: receive time, sending switch and text."""

    epoch_ns: int
    switch: str
    text: str


def _fail(where: str, text: str) -> NoReturn:
    msg = f"{where}: {text}"
    raise LabTestError(msg)


def _fields(raw: Any, where: str, fields: tuple[tuple[str, ...], ...]) -> dict:
    required, optional = fields
    if not isinstance(raw, dict):
        _fail(where, "must be a mapping")
    if unknown := set(raw) - {*required, *optional}:
        allowed = ", ".join((*required, *optional))
        _fail(where, f"unknown field {', '.join(sorted(unknown))}; allowed: {allowed}")
    if missing := [key for key in required if key not in raw]:
        _fail(where, f"missing field {', '.join(missing)}")
    return raw


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(where, "must be text")
    return value


def _list(value: Any, where: str) -> list:
    if not isinstance(value, list) or not value:
        _fail(where, "must be a non-empty list")
    return value


def _seconds(value: Any, where: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value < 0
    ):
        _fail(where, "must be a number of seconds, 0 or more")
    return float(value)


def _point(value: Any, where: str) -> str:
    try:
        return str(lab.point(_text(value, where)))
    except lab.LabError as error:
        _fail(where, error.message)


def _read_yaml(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
        return yaml.load(text, Loader=intent._UniqueKeyLoader)  # noqa: S506 - a SafeLoader subclass
    except (OSError, yaml.YAMLError) as error:
        msg = f"{path}: cannot read the file: {error}"
        raise LabTestError(msg) from None


def _optional_text(raw: Mapping[str, Any], key: str, where: str) -> str | None:
    value = raw.get(key)
    return None if value is None else _text(value, f"{where}: {key}")


def _statements(raw: Any, where: str) -> tuple[Statement, ...]:
    """The state of a lab file: a list of statements, each with its intent checks."""
    statements = []
    for n, entry in enumerate(_list(raw, where), 1):
        at = f"{where} {n}"
        _fields(entry, at, STATEMENT_FIELDS)
        text = _text(entry["statement"], f"{at}: statement")
        source = _optional_text(entry, "source", at)
        try:
            checks = tuple(
                intent.parse_item(item, f"{at}: check {m}")
                for m, item in enumerate(_list(entry["checks"], f"{at}: checks"), 1)
            )
        except intent.IntentError as error:
            raise LabTestError(error.message) from None
        statements.append(Statement(text, source, checks))
    return tuple(statements)


def _streams(raw: Any, where: str) -> tuple[StreamSpec, ...]:
    """The streams of a lab file; the ICMP identifier is the position in the file."""
    streams: list[StreamSpec] = []
    for n, entry in enumerate(_list(raw, where), 1):
        at = f"{where} {n}"
        _fields(entry, at, STREAM_FIELDS)
        name = _text(entry["name"], f"{at}: name")
        if not NAME.fullmatch(name):
            _fail(f"{at}: name", "must be letters, digits, dots, dashes or underscores")
        if name in (s.name for s in streams):
            _fail(f"{at}: name", f"stream {name} is listed twice")
        streams.append(
            StreamSpec(
                name,
                n,
                _point(entry["from"], f"{at}: from"),
                _point(entry["to"], f"{at}: to"),
            )
        )
    return tuple(streams)


def _rules(raw: Any, where: str) -> tuple[Rule, ...]:
    _fields(raw, where, LOG_FIELDS)
    if not raw:
        _fail(where, "needs must or must_not")
    rules = []
    for kind in LOG_FIELDS[1]:
        for n, entry in enumerate(
            _list(raw[kind], f"{where}: {kind}") if kind in raw else [], 1
        ):
            at = f"{where}: {kind} {n}"
            _fields(entry, at, RULE_FIELDS)
            rules.append(
                Rule(
                    kind,
                    _text(entry["switch"], f"{at}: switch"),
                    _text(entry["text"], f"{at}: text"),
                )
            )
    return tuple(rules)


def _switch_log(raw: Mapping[str, Any], where: str) -> str | None:
    value = _optional_text(raw, "switch_log", where)
    if value is not None:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            _fail(
                f"{where}: switch_log",
                "must be a path inside the containerlab lab folder",
            )
    return value


def load_test(path: str | Path, lab_file: Path | None = None) -> LabTest:
    """Read and strictly validate a test file and its lab file.

    The lab path is relative to the test file. With `lab_file`, as in a saved
    evidence folder, the lab file is read from there instead.
    """
    path = Path(path)
    raw = _fields(_read_yaml(path), f"{path}", TEST_FIELDS)
    name = _text(raw["name"], f"{path}: name")
    lab_path = lab_file or path.parent / _text(raw["lab"], f"{path}: lab")
    if not lab_path.is_file():
        _fail(f"{path}: lab", f"there is no lab file {lab_path}")
    lab_raw = _fields(_read_yaml(lab_path), f"{lab_path}", LAB_FIELDS)
    statements = _statements(lab_raw["state"], f"{lab_path}: state")
    streams = _streams(lab_raw["streams"], f"{lab_path}: stream")
    switch_log = _switch_log(lab_raw, f"{lab_path}")
    names = [s.name for s in streams]
    test_rules = _rules(raw["log"], f"{path}: log") if "log" in raw else ()
    steps: list[Step] = []
    for n, entry in enumerate(_list(raw["steps"], f"{path}: steps"), 1):
        where = f"{path}: step {n}"
        _fields(entry, where, STEP_FIELDS)
        step_name = _text(entry["name"], f"{where}: name")
        if step_name == QUIET or step_name in (s.name for s in steps):
            _fail(f"{where}: name", f"{step_name!r} is taken")
        if entry["state"] not in ("down", "up"):
            _fail(f"{where}: state", "must be down or up")
        limits = entry["max_outage_s"]
        if not isinstance(limits, dict) or sorted(limits) != sorted(names):
            _fail(
                f"{where}: max_outage_s",
                f"must give a limit for each stream of {lab_path}: {', '.join(names)}",
            )
        steps.append(
            Step(
                step_name,
                _point(entry["cable"], f"{where}: cable"),
                entry["state"],
                _seconds(entry["hold_s"], f"{where}: hold_s"),
                tuple(
                    (s, _seconds(limits[s], f"{where}: max_outage_s: {s}"))
                    for s in names
                ),
                _text(entry["expected"], f"{where}: expected"),
                _rules(entry["log"], f"{where}: log") if "log" in entry else (),
            )
        )
    if switch_log is None and (test_rules or any(s.log for s in steps)):
        _fail(f"{path}: log", f"log rules need switch_log in {lab_path}")
    try:
        intent.validate_intent([item for s in statements for item in s.checks])
    except intent.IntentError as error:
        raise LabTestError(error.message) from None
    return LabTest(
        path,
        path.read_text(encoding="utf-8"),
        name,
        _text(raw["purpose"], f"{path}: purpose"),
        _optional_text(raw, "source", f"{path}"),
        lab_path.read_text(encoding="utf-8"),
        statements,
        streams,
        switch_log,
        test_rules,
        tuple(steps),
    )


def judge(outage: Mapping[str, Any] | None, limit: float) -> tuple[Verdict, str]:
    """The verdict of one stream's outage in one step against its limit.

    A 0 s limit allows no lost and no late ping. Otherwise pass when the upper
    bound is at most the limit, and fail when the lower bound is above it. A
    lost ping makes the outage longer than its lower bound, so a lower bound
    equal to the limit also fails. Bounds that straddle the limit cannot
    decide, which is error.
    """
    if outage is None:
        return "pass", traffic.lost_text(0, None, None)
    lower, upper = outage["lower_s"], outage["upper_s"]
    text = traffic.lost_text(outage["lost"], lower, upper)
    if limit == 0:
        return "fail", f"{text}, and a 0 s limit allows no lost or late ping"
    if lower > limit or (outage["lost"] and lower >= limit):
        return "fail", f"{text}, above {limit:g} s"
    if upper is not None and upper <= limit:
        return "pass", f"{text}, within {limit:g} s"
    return "error", f"{text}, which straddles {limit:g} s"


def rollup(verdicts: Sequence[Verdict]) -> Verdict:
    """fail if anything fails, else error if anything is error, else pass."""
    return "fail" if "fail" in verdicts else "error" if "error" in verdicts else "pass"


def marker(test: LabTest, which: str) -> str:
    """The log marker that proves a switch's log reaches the collector."""
    return f"networka {test.name} {which}"


def parse_log(text: str) -> list[LogLine]:
    """The lines of a switch log: RFC 3339 receive time, switch name, text.

    A line without an RFC 3339 time with a zone is not a switch log line and is skipped.
    """
    lines = []
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    for raw in text.splitlines():
        stamp, _, rest = raw.partition(" ")
        switch, _, message = rest.partition(" ")
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            continue
        if when.tzinfo is None or not switch:
            continue
        lines.append(
            LogLine((when - epoch) // timedelta(microseconds=1) * 1000, switch, message)
        )
    return lines


def _fill_hosts(client: NetworkaClient, the_lab: lab.Lab) -> None:
    """Give each inventory device without a host the management address of its lab node."""
    for name, node in the_lab.nodes.items():
        device = client.devices.get(name)
        if device is not None and not device.host:
            device.host = node.address


def _switches(client: NetworkaClient, the_lab: lab.Lab) -> list[str]:
    """The lab nodes whose platform module can write a log marker."""
    found = []
    for name in sorted(the_lab.nodes):
        device = client.devices.get(name)
        module = intent.PLATFORMS.get(device.device_type) if device else None
        if module and hasattr(importlib.import_module(module), "log_marker"):
            found.append(name)
    return found


def _markers(
    client: NetworkaClient,
    session: lab.Session,
    switches: Sequence[str],
    text: str,
    which: str,
    run_options: Mapping[str, Any],
) -> None:
    errors = {}
    for switch in switches:
        module = intent.platform(client.devices[switch].device_type)
        if error := module.log_marker(client, switch, text, **run_options):
            errors[switch] = error
    session.mark(
        "log_marker", which=which, text=text, switches=list(switches), errors=errors
    )


def _added(path: Path, offset: int | None) -> bytes | None:
    """What was added to the switch log since `offset`, or None without the file."""
    if offset is None or not path.is_file():
        return None
    data = path.read_bytes()
    return data[offset:] if len(data) >= offset else data


def run_test(
    client: NetworkaClient,
    test: LabTest,
    lab_dir: str | Path,
    save_dir: str | Path,
    **run_options: Any,
) -> dict[str, Any]:
    """Run one test in a deployed lab and save its evidence; return result.json.

    The evidence goes to `<save_dir>/<test file name>/`, which must not hold
    evidence yet. `run_options` are passed to the intent runs.
    """
    folder = Path(save_dir) / test.path.stem
    if folder.exists() and any(folder.iterdir()):
        msg = f"{folder} already holds evidence; save to another directory"
        raise LabTestError(msg)
    lab_dir = Path(lab_dir)
    the_lab = lab.load_lab(lab_dir)
    for where in test.ends():
        the_lab.node(lab.point(where).node)
    cables = {
        str(end)
        for step in test.steps
        for end in (lab.point(step.cable), the_lab.peer(lab.point(step.cable)))
    }
    _fill_hosts(client, the_lab)
    switches = _switches(client, the_lab) if test.switch_log else []
    if test.switch_log and not switches:
        msg = f"lab {the_lab.name} has no device that can write a log marker"
        raise LabTestError(msg)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / TEST_FILE).write_text(test.text, encoding="utf-8")
    (folder / LAB_FILE).write_text(test.lab_text, encoding="utf-8")
    items = test.items()
    log_path = lab_dir / test.switch_log if test.switch_log else None
    with lab.Session(the_lab, folder) as session:
        session.mark("test_started", test=test.name, lab=the_lab.name)
        offset = None
        if log_path is not None:
            offset = log_path.stat().st_size if log_path.is_file() else None
            _markers(
                client, session, switches, marker(test, "start"), "start", run_options
            )
        before = intent.run_intent(
            client, items, folder / "state-before", **run_options
        )
        session.mark("state_checked", when="before", verdict=before.verdict)
        if before.verdict == "pass":
            try:
                _flow(client, test, session, items, sorted(cables), run_options)
            except lab.LabError as error:
                session.mark("run_error", reason=error.message)
        if log_path is not None:
            end = marker(test, "end")
            _markers(client, session, switches, end, "end", run_options)
            deadline = time.monotonic() + MARKER_WAIT_S
            added = _added(log_path, offset)
            while added is not None and time.monotonic() < deadline:
                seen = {
                    line.switch
                    for line in parse_log(added.decode(errors="replace"))
                    if end.lower() in line.text.lower()
                }
                if seen >= set(switches):
                    break
                time.sleep(0.05)
                added = _added(log_path, offset)
            if added is not None:
                (folder / SYSLOG_FILE).write_bytes(added)
    result = evaluate(folder)
    (folder / RESULT_FILE).write_text(json.dumps(result, indent=2) + "\n")
    (folder / TIMELINE_FILE).write_text(timeline(folder, result))
    return result


def _streams_of(test: LabTest) -> list[traffic.Stream]:
    return [
        traffic.Stream(s.name, s.ident, s.source, s.destination) for s in test.streams
    ]


def _first_replies(pcaps: Mapping[str, Path], streams: Sequence[traffic.Stream]) -> int:
    """The epoch ns by which every stream had its first reply, read from the captures.

    A capture that holds no packet yet cannot be decoded, so it counts as no reply.
    """
    deadline = time.monotonic() + FIRST_REPLY_S
    while True:
        firsts: dict[str, int | None] = {}
        for stream in streams:
            try:
                frames = traffic.decode(pcaps[stream.source])
            except subprocess.SubprocessError:
                frames = {}
            firsts[stream.name] = traffic.first_reply(frames, stream.ident)
        found = [v for v in firsts.values() if v is not None]
        if len(found) == len(streams):
            return max(found)
        if time.monotonic() > deadline:
            silent = ", ".join(n for n, v in firsts.items() if v is None)
            msg = f"no reply within {FIRST_REPLY_S:g} s for {silent}"
            raise lab.LabError(msg)
        time.sleep(0.1)


def _flow(
    client: NetworkaClient,
    test: LabTest,
    session: lab.Session,
    items: list[IntentItem],
    cables: list[str],
    run_options: Mapping[str, Any],
) -> None:
    pcaps = session.start_captures(sorted(test.ends() | set(cables)))
    for stream in test.streams:
        session.start_stream(
            stream.ident,
            stream.name,
            stream.source,
            stream.destination,
            traffic.INTERVAL_NS / NS,
        )
    streams = _streams_of(test)
    start = _first_replies(pcaps, streams)
    end = start + round(QUIET_S * NS)
    time.sleep(max(0.0, (end - time.time_ns()) / NS + SETTLE_S))
    try:
        measured = traffic.measure(pcaps, streams, [traffic.Window(QUIET, start, end)])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        msg = f"the captures cannot be decoded: {error}"
        raise lab.LabError(msg) from error
    problems = traffic.quiet_problems(traffic.quiet(measured, QUIET))
    session.mark("quiet_checked", start_ns=start, problems=problems)
    if problems:
        return
    for step in test.steps:
        session.mark("step_start", step=step.name)
        session.set_link(step.cable, step.state)
        time.sleep(step.hold_s)
    session.mark("steps_end")
    time.sleep(SETTLE_S)
    after = intent.run_intent(
        client, items, session.directory / "state-after", **run_options
    )
    session.mark("state_checked", when="after", verdict=after.verdict)


def _events(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    except (OSError, ValueError) as error:
        msg = f"{path}: cannot read the events: {error}"
        raise LabTestError(msg) from None


def _state(test: LabTest, folder: Path) -> dict[str, Any] | None:
    """The statements and their checks, replayed from one saved intent run."""
    if not (folder / intent.EVIDENCE_FILE).is_file():
        return None
    try:
        evidence = intent.load_json((folder / intent.EVIDENCE_FILE).read_text())
        report = intent.replay_intent(test.items(), evidence)
    except (OSError, ValueError, intent.IntentError) as error:
        msg = f"{folder}: cannot replay the state: {error}"
        raise LabTestError(msg) from None
    results = iter(report.results)
    statements: list[dict[str, Any]] = []
    for statement in test.statements:
        checks: list[dict[str, Any]] = []
        for item, outcome in (next(results) for _ in statement.checks):
            checks.append(
                {
                    "name": item.name,
                    "device": item.device,
                    "check": item.check,
                    "params": item.params,
                    "expected": outcome.expected,
                    "observed": outcome.observed,
                    "verdict": outcome.verdict,
                    "reason": outcome.reason,
                }
            )
        statements.append(
            {
                "statement": statement.statement,
                "source": statement.source,
                "verdict": rollup([c["verdict"] for c in checks]),
                "checks": checks,
            }
        )
    return {
        "verdict": rollup([s["verdict"] for s in statements]),
        "statements": statements,
    }


def _zero(events: Sequence[Mapping[str, Any]]) -> int:
    """The start of the quiet window, or the first event when there was none."""
    quiet = next((e for e in events if e["name"] == "quiet_checked"), None)
    return quiet["start_ns"] if quiet else events[0]["epoch_ns"]


@dataclass(frozen=True)
class SwitchLog:
    """The saved switch log with the span between each switch's two markers."""

    lines: list[LogLine]
    switches: list[str]
    spans: dict[str, tuple[int, int]]


def _judge_rules(
    rules: Sequence[Rule],
    log: SwitchLog,
    spans: Mapping[str, tuple[int, int]],
    zero: int,
) -> list[dict[str, Any]]:
    """Each rule with its verdict and the lines that match it within each switch's span.

    A switch without a span has no proven log path, so its rules are error.
    """
    judged = []
    for rule in rules:
        targets = log.switches if rule.switch == EVERY else [rule.switch]
        unproven = [s for s in targets if s not in spans]
        hits: dict[str, list[LogLine]] = {}
        for switch in targets:
            if (window := spans.get(switch)) is not None:
                hits[switch] = [
                    line
                    for line in log.lines
                    if line.switch == switch
                    and window[0] <= line.epoch_ns <= window[1]
                    and rule.text.lower() in line.text.lower()
                ]
        verdict: Verdict
        if unproven:
            verdict = "error"
            reason = (
                f"the log path of {', '.join(unproven)} is not proven by both markers"
            )
        elif rule.kind == "must":
            silent = [s for s in targets if not hits[s]]
            verdict = "fail" if silent else "pass"
            reason = f"{', '.join(silent)} did not log it" if silent else "logged"
        else:
            loud = [s for s in targets if hits[s]]
            verdict = "fail" if loud else "pass"
            reason = f"{', '.join(loud)} logged it" if loud else "not logged"
        judged.append(
            {
                "kind": rule.kind,
                "switch": rule.switch,
                "text": rule.text,
                "verdict": verdict,
                "reason": reason,
                "lines": [
                    {
                        "time_s": traffic.seconds(line.epoch_ns - zero),
                        "switch": line.switch,
                        "text": line.text,
                    }
                    for found in hits.values()
                    for line in found
                ],
            }
        )
    return judged


def _read_switch_log(
    test: LabTest, folder: Path, events: Sequence[Mapping[str, Any]], part: Any
) -> tuple[SwitchLog | None, dict[str, Any] | None]:
    """The saved switch log, its markers and its line counts; a missing marker is error."""
    if test.switch_log is None:
        return None, None
    starts = [e for e in events if e["name"] == "log_marker" and e["which"] == "start"]
    ends = [e for e in events if e["name"] == "log_marker" and e["which"] == "end"]
    if not starts or not (folder / SYSLOG_FILE).is_file():
        part(
            "error",
            f"The switch log {test.switch_log} was not saved, so the log rules are not judged.",
        )
        return None, {"file": test.switch_log, "saved": False}
    switches = starts[0]["switches"]
    lines = parse_log((folder / SYSLOG_FILE).read_text(errors="replace"))
    texts = {"start": starts[0]["text"], "end": ends[0]["text"] if ends else None}
    markers: dict[str, dict[str, int | None]] = {}
    for switch in switches:
        markers[switch] = {
            which: next(
                (
                    line.epoch_ns
                    for line in lines
                    if text
                    and line.switch == switch
                    and text.lower() in line.text.lower()
                ),
                None,
            )
            for which, text in texts.items()
        }
        for which, at in markers[switch].items():
            if at is None:
                part(
                    "error",
                    f"{switch} did not log the {which} marker, so its log path is not proven.",
                )
    spans = {
        s: (m["start"], m["end"])
        for s, m in markers.items()
        if m["start"] is not None and m["end"] is not None
    }
    zero = _zero(events)
    summary = {
        "file": test.switch_log,
        "saved": True,
        "lines": dict(sorted(Counter(line.switch for line in lines).items())),
        "markers": {
            s: {
                w: None if t is None else traffic.seconds(t - zero)
                for w, t in m.items()
            }
            for s, m in markers.items()
        },
    }
    return SwitchLog(lines, switches, spans), summary


def evaluate(folder: str | Path) -> dict[str, Any]:
    """Compute result.json from the files of one evidence folder, without the lab."""
    folder = Path(folder)
    test = load_test(folder / TEST_FILE, folder / LAB_FILE)
    events = _events(folder / EVENTS_FILE)
    marks: dict[str, dict[str, Any]] = {}
    for event in events:
        marks.setdefault(event["name"], event)
    parts: list[Verdict] = []
    reasons: list[str] = []
    result: dict[str, Any] = {
        "name": test.name,
        "purpose": test.purpose,
        "source": test.source,
        "verdict": "error",
        "reasons": reasons,
        "state": {},
        "quiet": None,
        "steps": [],
        "log": [],
        "switch_log": None,
        "validity": [],
        "traffic": None,
    }

    def part(verdict: Verdict, reason: str) -> None:
        parts.append(verdict)
        if verdict != "pass":
            reasons.append(reason)

    before = _state(test, folder / "state-before")
    result["state"]["before"] = before
    if before is None:
        part("error", "The state before the test was not checked.")
    else:
        part(
            before["verdict"],
            f"The state before the test is {before['verdict']}, so no cable was changed.",
        )
    log, result["switch_log"] = _read_switch_log(test, folder, events, part)
    if log is not None:
        result["log"] = _judge_rules(test.log, log, log.spans, _zero(events))
        for rule in result["log"]:
            part(
                rule["verdict"],
                f"Log rule {rule['kind']} {rule['text']!r} on {rule['switch']} is "
                f"{rule['verdict']}: {rule['reason']}.",
            )
    if "run_error" in marks:
        part("error", f"The run stopped: {marks['run_error']['reason']}")
    if marks.get("quiet_checked", {}).get("problems"):
        problems = "; ".join(marks["quiet_checked"]["problems"])
        part(
            "error",
            f"The quiet window was not clean, so no cable was changed: {problems}",
        )
    if "steps_end" in marks:
        _traffic(test, folder, events, marks, result, log, part)
        after = _state(test, folder / "state-after")
        result["state"]["after"] = after
        if after is None:
            part("error", "The state after the test was not checked.")
        else:
            part(after["verdict"], f"The state after the test is {after['verdict']}.")
    elif before is not None and before["verdict"] == "pass" and not reasons:
        part("error", "The steps did not finish.")
    result["verdict"] = rollup(parts)
    return result


def _traffic(
    test: LabTest,
    folder: Path,
    events: list[dict[str, Any]],
    marks: Mapping[str, dict[str, Any]],
    result: dict[str, Any],
    log: SwitchLog | None,
    part: Any,
) -> None:
    """Measure the streams, judge the steps and record the validity checks.

    Only the captures at the ends of the streams count. Cable captures are
    diagnostics and never change the verdict.
    """
    validity: list[dict[str, Any]] = result["validity"]

    def check(ok: object, text: str) -> None:
        validity.append({"check": text, "ok": bool(ok)})
        if not ok:
            part("error", f"Not valid: {text}.")

    starts = [e for e in events if e["name"] == "step_start"]
    if [e["step"] for e in starts] != [s.name for s in test.steps]:
        part("error", "The step events do not match the steps of the test.")
        return
    edges = [e["epoch_ns"] for e in starts] + [marks["steps_end"]["epoch_ns"]]
    windows = [traffic.Window(QUIET, marks["quiet_checked"]["start_ns"], edges[0])]
    windows += [
        traffic.Window(step.name, edges[n], edges[n + 1])
        for n, step in enumerate(test.steps)
    ]
    pcaps = {
        e["point"]: folder / e["pcap"] for e in events if e["name"] == "capture_started"
    }
    for where in sorted(test.ends()):
        pcap = pcaps.get(where)
        if pcap is None:
            check(False, f"capture at {where} started")
            continue
        found = traffic.check_capture(pcap, pcap.with_suffix(".log"))
        check(found["valid"], f"capture at {where} is complete and dropped no packet")
    stopped = marks.get("stopped", {})
    judged = test.ends() | {s.name for s in test.streams}
    early = [name for name in stopped.get("early_exits", []) if name in judged]
    check("stopped" in marks and not early, "every stream and its captures stayed up")
    check(not stopped.get("restore_errors"), "every cable set down was set up again")
    check(
        abs(stopped.get("clock_delta_ns", CLOCK_LIMIT_NS)) < CLOCK_LIMIT_NS,
        "the wall clock and the monotonic clock of the lab host agree within 50 ms",
    )
    try:
        measured = traffic.measure(pcaps, _streams_of(test), windows)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        check(False, f"the captures can be decoded ({error})")
        return
    result["traffic"] = measured
    for name, flow in measured["streams"].items():
        limit_ms = round(flow["send_gap_limit_s"] * 1000)
        check(flow["cadence_ok"], f"{name} sent a ping at least every {limit_ms} ms")
        check(
            not flow["capture_mismatches"],
            f"{name} shows the same replies at both capture points",
        )
    quiet = traffic.quiet(measured, QUIET)
    result["quiet"] = quiet
    for name, counts in quiet["streams"].items():
        check(
            counts["ok"],
            f"{name} delivered {counts['min_delivered']} pings or more in the quiet "
            f"window at one ping every {traffic.INTERVAL_NS // 1_000_000} ms, "
            "none lost or duplicated",
        )
    zero = measured["start_ns"]
    for n, step in enumerate(test.steps):
        window = measured["windows"][step.name]
        streams: dict[str, Any] = {}
        for name, limit in step.limits:
            counts = window["streams"][name]
            outage = counts["outage"]
            verdict, reason = judge(outage, limit)
            if counts["duplicates"] and verdict != "fail":
                verdict, reason = "fail", f"{counts['duplicates']} duplicated pings"
            streams[name] = {
                "interval_s": measured["interval_s"],
                "limit_s": limit,
                "lower_s": outage["lower_s"] if outage else 0.0,
                "upper_s": outage["upper_s"] if outage else 0.0,
                "lost": counts["lost"],
                "summary": counts["summary"],
                "duplicates": counts["duplicates"],
                "sent": counts["sent"],
                "delivered": counts["delivered"],
                "verdict": verdict,
                "reason": reason,
            }
        span = (edges[n], edges[n + 1] - 1)
        spans = dict.fromkeys(log.spans, span) if log else {}
        rules = _judge_rules(step.log, log, spans, zero) if log else []
        verdict = rollup(
            [s["verdict"] for s in streams.values()] + [r["verdict"] for r in rules]
        )
        result["steps"].append(
            {
                "name": step.name,
                "expected": step.expected,
                "cable": step.cable,
                "state": step.state,
                "hold_s": step.hold_s,
                "start_s": window["start_s"],
                "end_s": window["end_s"],
                "verdict": verdict,
                "streams": streams,
                "log": rules,
            }
        )
        part(verdict, f"Step {step.name} is {verdict}.")


def _event_row(event: Mapping[str, Any]) -> tuple[str, str] | None:
    """What an event was and a short detail in words, or None for no row."""
    name = event["name"]
    if name == "test_started":
        return "test", f"{event['test']} started in lab {event['lab']}"
    if name == "log_marker":
        errors = "".join(f", {s} failed: {e}" for s, e in event["errors"].items())
        return (
            "switch log",
            f"marker {event['text']!r} written on {', '.join(event['switches'])}{errors}",
        )
    if name == "state_checked":
        return "state", f"check {event['when']} the steps: {event['verdict']}"
    if name == "capture_started":
        return "capture", f"started at {event['point']}"
    if name == "stream_started":
        return (
            event["stream"],
            f"started from {event['source']} to {event['destination']} at {event['address']}",
        )
    if name == "quiet_checked":
        problems = "; ".join(event["problems"])
        return QUIET, f"not clean: {problems}" if problems else "clean"
    if name == "step_start":
        return "step", event["step"]
    if name == "link_applied":
        return "cable", f"{event['point']} set {event['state']}"
    if name == "link_observed":
        if not event["confirmed"]:
            return "cable", f"{event['point']} is not {event['state']} at the far end"
        far = ", ".join(event["far"])
        seen = (
            f", seen at {far} after {event['latency_s'] * 1000:.0f} ms" if far else ""
        )
        return "cable", f"{event['point']} {event['state']} at both ends{seen}"
    if name == "steps_end":
        return "steps", "last step ended"
    if name == "run_error":
        return "run error", event["reason"]
    if name == "stopped":
        notes = (
            [f"ended early: {', '.join(event['early_exits'])}"]
            if event["early_exits"]
            else []
        )
        notes += [f"not set up again: {e}" for e in event["restore_errors"]]
        return "stopped", "; ".join(["captures and streams stopped", *notes])
    return None


def timeline(folder: str | Path, result: Mapping[str, Any]) -> str:
    """timeline.tsv: seconds from the start of the quiet window, what happened, a detail."""
    folder = Path(folder)
    events = _events(folder / EVENTS_FILE)
    zero = _zero(events)
    rows = []
    for event in events:
        if (row := _event_row(event)) is not None:
            rows.append((event["epoch_ns"] - zero, *row))
    if (
        quiet := next((e for e in events if e["name"] == "quiet_checked"), None)
    ) is not None:
        rows.append(
            (
                quiet["start_ns"] - zero,
                QUIET,
                "starts at the first reply of every stream",
            )
        )
    for name, flow in ((result.get("traffic") or {}).get("streams") or {}).items():
        for gap in flow["gaps"]:
            where = ", ".join(gap["where"]) or "not sent"
            rows.append(
                (round(gap["begins_s"] * NS), name, f"{gap['summary']}, {where}")
            )
    if (folder / SYSLOG_FILE).is_file():
        for line in parse_log((folder / SYSLOG_FILE).read_text(errors="replace")):
            rows.append((line.epoch_ns - zero, f"{line.switch} log", line.text))
    lines = ["time_s\twhat\tdetail"]
    lines += [f"{t / NS:.3f}\t{what}\t{text}" for t, what, text in sorted(rows)]
    return "\n".join(lines) + "\n"


def replay(folder: str | Path) -> tuple[dict[str, Any], bool]:
    """Compute result.json again and write timeline.tsv again from the saved files.

    Also say if the result equals the saved result.json.
    """
    folder = Path(folder)
    computed = evaluate(folder)
    try:
        saved = json.loads((folder / RESULT_FILE).read_text())
    except (OSError, ValueError) as error:
        msg = f"{folder / RESULT_FILE}: cannot read the saved result: {error}"
        raise LabTestError(msg) from None
    (folder / TIMELINE_FILE).write_text(timeline(folder, computed))
    return computed, computed == saved
