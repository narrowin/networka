# SPDX-License-Identifier: MIT
"""Lab tests: a test file, its fixed flow in a containerlab lab, the verdict and replay.

A test file names state files, numbered ping streams and ordered steps. A step
can set one link down or up, holds for a time and limits the outage of the
streams it lists. The flow checks the state, starts captures and streams,
checks a baseline window, runs the steps, checks the state again and stops.

The verdict is computed from the saved evidence only. `replay` therefore
computes the same `result.json` again without the lab.
"""

from __future__ import annotations

import ipaddress
import json
import math
import re
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

import yaml

from network_toolkit import intent, lab, traffic
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.intent import IntentItem, Verdict

if TYPE_CHECKING:
    from network_toolkit.client import NetworkaClient

TEST_FILE = "test.yaml"
STATE_DIR = "state"
EVENTS_FILE = "events.jsonl"
RESULT_FILE = "result.json"
TIMELINE_FILE = "timeline.tsv"
INTERVAL_S = 0.1
# Time for neighbour discovery between the start of the streams and the baseline.
NEIGHBOUR_S = 2.0
BASELINE_S = 5.0
# Time after the last step for late replies, before the state is checked again.
SETTLE_S = 2.0
CLOCK_LIMIT_NS = 50_000_000
BASELINE = "baseline"

TEST_FIELDS = (("name", "state", "streams", "steps"), ("source", "captures"))
STREAM_FIELDS = (("id", "from", "to"), ("address",))
STEP_FIELDS = (("name", "hold_s", "expect"), ("action",))
ACTION_FIELDS = (("link", "state"), ())
EXPECT_FIELDS = (("streams", "max_outage_s"), ())
STATEMENT_FIELDS = (("statement", "checks"), ("source",))

PING_LINE = re.compile(
    r"^\[(\d+\.\d+)\] (?:\d+ bytes from .*icmp_seq=(\d+)(.*)|no answer yet for icmp_seq=(\d+))$"
)


class LabTestError(NetworkToolkitError):
    """A test file, a state file or saved evidence cannot be used."""


@dataclass(frozen=True)
class StreamSpec:
    id: int
    source: str
    destination: str
    address: str | None


@dataclass(frozen=True)
class Action:
    link: str
    state: str


@dataclass(frozen=True)
class Expect:
    streams: tuple[int, ...]
    max_outage_s: float


@dataclass(frozen=True)
class Step:
    name: str
    action: Action | None
    hold_s: float
    expect: tuple[Expect, ...]


@dataclass(frozen=True)
class Statement:
    statement: str
    source: str | None
    checks: tuple[IntentItem, ...]


@dataclass(frozen=True)
class LabTest:
    """A validated test file with its state files."""

    path: Path
    text: str
    name: str
    source: str | None
    state_files: tuple[tuple[str, str], ...]
    statements: tuple[Statement, ...]
    streams: tuple[StreamSpec, ...]
    captures: tuple[str, ...]
    steps: tuple[Step, ...]

    def items(self) -> list[IntentItem]:
        """Every check of every statement, in file order."""
        return [item for s in self.statements for item in s.checks]


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


def load_state(path: Path) -> tuple[Statement, ...]:
    """Read a state file: a list of statements, each with its intent checks."""
    data = _list(_read_yaml(path), f"{path}")
    statements = []
    for n, raw in enumerate(data, 1):
        where = f"{path}: statement {n}"
        _fields(raw, where, STATEMENT_FIELDS)
        text = _text(raw["statement"], f"{where}: statement")
        source = raw.get("source")
        if source is not None:
            _text(source, f"{where}: source")
        try:
            checks = tuple(
                intent.parse_item(item, f"{where}: check {m}")
                for m, item in enumerate(_list(raw["checks"], f"{where}: checks"), 1)
            )
        except intent.IntentError as error:
            raise LabTestError(error.message) from None
        statements.append(Statement(text, source, checks))
    return tuple(statements)


def load_test(path: str | Path, state_dir: Path | None = None) -> LabTest:
    """Read and strictly validate a test file and its state files.

    State paths are relative to the test file. With `state_dir`, as in a saved
    evidence folder, each state file is read from there by its file name.
    """
    path = Path(path)
    raw = _fields(_read_yaml(path), f"{path}", TEST_FIELDS)
    name = _text(raw["name"], f"{path}: name")
    source = raw.get("source")
    if source is not None:
        _text(source, f"{path}: source")
    state_files: list[tuple[str, str]] = []
    statements: list[Statement] = []
    for n, entry in enumerate(_list(raw["state"], f"{path}: state"), 1):
        relative = Path(_text(entry, f"{path}: state {n}"))
        if relative.name in (known for known, _ in state_files):
            _fail(f"{path}: state {n}", f"a second state file named {relative.name}")
        file = (state_dir or path.parent / relative.parent) / relative.name
        statements.extend(load_state(file))
        state_files.append((relative.name, file.read_text(encoding="utf-8")))
    streams: list[StreamSpec] = []
    for n, entry in enumerate(_list(raw["streams"], f"{path}: streams"), 1):
        where = f"{path}: stream {n}"
        _fields(entry, where, STREAM_FIELDS)
        ident = entry["id"]
        if (
            isinstance(ident, bool)
            or not isinstance(ident, int)
            or not 0 < ident < 65536
        ):
            _fail(f"{where}: id", "must be a number from 1 to 65535")
        if ident in (s.id for s in streams):
            _fail(f"{where}: id", f"stream {ident} is listed twice")
        address = entry.get("address")
        if address is not None:
            try:
                ipaddress.IPv4Address(_text(address, f"{where}: address"))
            except ValueError:
                _fail(f"{where}: address", "must be an IPv4 address")
        streams.append(
            StreamSpec(
                ident,
                _point(entry["from"], f"{where}: from"),
                _point(entry["to"], f"{where}: to"),
                address,
            )
        )
    extra = []
    if "captures" in raw:
        captures = _list(raw["captures"], f"{path}: captures")
        extra = [_point(p, f"{path}: captures {n}") for n, p in enumerate(captures, 1)]
    ends = {point for s in streams for point in (s.source, s.destination)}
    steps: list[Step] = []
    for n, entry in enumerate(_list(raw["steps"], f"{path}: steps"), 1):
        where = f"{path}: step {n}"
        _fields(entry, where, STEP_FIELDS)
        step_name = _text(entry["name"], f"{where}: name")
        if step_name == BASELINE or step_name in (s.name for s in steps):
            _fail(f"{where}: name", f"{step_name!r} is taken")
        action = None
        if entry.get("action") is not None:
            act = _fields(entry["action"], f"{where}: action", ACTION_FIELDS)
            if act["state"] not in ("down", "up"):
                _fail(f"{where}: action: state", "must be down or up")
            action = Action(_point(act["link"], f"{where}: action: link"), act["state"])
        expects: list[Expect] = []
        listed: set[int] = set()
        for m, item in enumerate(_list(entry["expect"], f"{where}: expect"), 1):
            at = f"{where}: expect {m}"
            _fields(item, at, EXPECT_FIELDS)
            ids = _list(item["streams"], f"{at}: streams")
            for ident in ids:
                if ident not in (s.id for s in streams):
                    _fail(f"{at}: streams", f"stream {ident!r} is not in streams")
                if ident in listed:
                    _fail(
                        f"{at}: streams",
                        f"stream {ident} is limited twice in this step",
                    )
                listed.add(ident)
            limit = _seconds(item["max_outage_s"], f"{at}: max_outage_s")
            expects.append(Expect(tuple(ids), limit))
        hold = _seconds(entry["hold_s"], f"{where}: hold_s")
        steps.append(Step(step_name, action, hold, tuple(expects)))
    try:
        intent.validate_intent([item for s in statements for item in s.checks])
    except intent.IntentError as error:
        raise LabTestError(error.message) from None
    return LabTest(
        path,
        path.read_text(encoding="utf-8"),
        name,
        source,
        tuple(state_files),
        tuple(statements),
        tuple(streams),
        tuple(sorted(ends | set(extra))),
        tuple(steps),
    )


def judge(outage: Mapping[str, Any] | None, limit: float) -> tuple[Verdict, str]:
    """The verdict of one stream's outage in one step against its limit.

    Pass when the upper bound is at most the limit. Fail when the lower bound
    is above it. A lost probe makes the outage longer than its lower bound, so
    a lower bound equal to the limit also fails. Otherwise the bounds straddle
    the limit, and the evidence cannot decide.
    """
    if outage is None:
        return "pass", "no outage"
    lower, upper, lost = outage["lower_s"], outage["upper_s"], outage["lost"]
    bounds = f"{lower:.3f} to {'?' if upper is None else f'{upper:.3f}'} s"
    if lower > limit or (lost and lower >= limit):
        return "fail", f"outage {bounds} is above {limit:g} s"
    if upper is not None and upper <= limit:
        return "pass", f"outage {bounds} is within {limit:g} s"
    return "error", f"outage {bounds} straddles {limit:g} s"


def rollup(verdicts: Sequence[Verdict]) -> Verdict:
    """fail if anything fails, else error if anything is error, else pass."""
    return "fail" if "fail" in verdicts else "error" if "error" in verdicts else "pass"


def live_baseline(
    folder: Path, streams: Sequence[StreamSpec], start_ns: int
) -> list[str]:
    """What keeps the baseline from being clean, read from the ping logs.

    Each stream needs 30 replies since `start_ns`, no unanswered probe and no
    duplicate reply. The captures judge the baseline again after the run.
    """
    problems = []
    for stream in streams:
        replies, duplicates, unanswered = set(), set(), set()
        log = folder / "streams" / f"{stream.id}.log"
        for line in log.read_text(errors="replace").splitlines():
            found = PING_LINE.match(line)
            if not found or int(Decimal(found[1]) * traffic.NS) < start_ns:
                continue
            if found[4]:
                unanswered.add(int(found[4]))
            elif "DUP!" in found[3]:
                duplicates.add(int(found[2]))
            else:
                replies.add(int(found[2]))
        lost = sorted(unanswered - replies)
        if len(replies) < traffic.BASELINE_MIN_DELIVERED or lost or duplicates:
            problems.append(
                f"stream {stream.id}: {len(replies)} replies, unanswered {lost}, "
                f"duplicated {sorted(duplicates)}"
            )
    return problems


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
    the_lab = lab.load_lab(Path(lab_dir))
    for where in (*test.captures, *(s.action.link for s in test.steps if s.action)):
        the_lab.node(lab.point(where).node)
    for step in test.steps:
        if step.action is not None:
            the_lab.peer(lab.point(step.action.link))
    (folder / STATE_DIR).mkdir(parents=True, exist_ok=True)
    (folder / TEST_FILE).write_text(test.text, encoding="utf-8")
    for file_name, text in test.state_files:
        (folder / STATE_DIR / file_name).write_text(text, encoding="utf-8")
    items = test.items()
    with lab.Session(the_lab, folder) as session:
        session.mark("test_started", test=test.name, lab=the_lab.name)
        before = intent.run_intent(
            client, items, folder / "state-before", **run_options
        )
        session.mark("state_checked", when="before", verdict=before.verdict)
        if before.verdict == "pass":
            try:
                _flow(client, test, session, items, run_options)
            except lab.LabError as error:
                session.mark("run_error", reason=error.message)
    result = evaluate(folder)
    (folder / RESULT_FILE).write_text(json.dumps(result, indent=2) + "\n")
    (folder / TIMELINE_FILE).write_text(timeline(folder, result))
    return result


def _flow(
    client: NetworkaClient,
    test: LabTest,
    session: lab.Session,
    items: list[IntentItem],
    run_options: Mapping[str, Any],
) -> None:
    for where in test.captures:
        session.start_capture(where)
    for stream in test.streams:
        session.start_stream(
            stream.id, stream.source, stream.destination, stream.address, INTERVAL_S
        )
    time.sleep(NEIGHBOUR_S)
    start = session.mark("baseline_start")
    time.sleep(BASELINE_S)
    problems = live_baseline(session.directory, test.streams, start["epoch_ns"])
    if problems:
        session.mark("baseline_rejected", problems=problems)
        return
    for step in test.steps:
        session.mark("step_start", step=step.name)
        if step.action is not None:
            session.set_link(step.action.link, step.action.state)
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


def evaluate(folder: str | Path) -> dict[str, Any]:
    """Compute result.json from the files of one evidence folder, without the lab."""
    folder = Path(folder)
    test = load_test(folder / TEST_FILE, folder / STATE_DIR)
    events = _events(folder / EVENTS_FILE)
    marks: dict[str, dict[str, Any]] = {}
    for event in events:
        marks.setdefault(event["name"], event)
    parts: list[Verdict] = []
    reasons: list[str] = []
    result: dict[str, Any] = {
        "name": test.name,
        "source": test.source,
        "verdict": "error",
        "reasons": reasons,
        "state": {},
        "baseline": None,
        "steps": [],
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
            f"The state before the test is {before['verdict']}, so no action was applied.",
        )
    if "run_error" in marks:
        part("error", f"The run stopped: {marks['run_error']['reason']}")
    if "baseline_rejected" in marks:
        problems = "; ".join(marks["baseline_rejected"]["problems"])
        part(
            "error", f"The baseline was not clean, so no action was applied: {problems}"
        )
    if "steps_end" in marks:
        _traffic(test, folder, events, marks, result, part)
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
    part: Any,
) -> None:
    """Measure the streams, judge the steps and record the validity checks."""
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
    windows = [traffic.Window(BASELINE, marks["baseline_start"]["epoch_ns"], edges[0])]
    windows += [
        traffic.Window(step.name, edges[n], edges[n + 1])
        for n, step in enumerate(test.steps)
    ]
    pcaps = {
        e["point"]: folder / e["pcap"] for e in events if e["name"] == "capture_started"
    }
    sums = {}
    sum_file = folder / "captures" / "pcap.sha256"
    if sum_file.is_file():
        for line in sum_file.read_text().splitlines():
            digest, _, name = line.partition("  ")
            sums[name] = digest
    for where in test.captures:
        pcap = pcaps.get(where)
        if pcap is None:
            check(False, f"capture at {where} started")
            continue
        found = traffic.check_capture(pcap, pcap.with_suffix(".log"))
        check(
            found["valid"] and sums.get(pcap.name) == found["sha256"],
            f"capture at {where} is complete, unchanged and dropped no packet",
        )
    stopped = marks.get("stopped", {})
    check(
        "stopped" in marks and not stopped["early_exits"],
        "every capture and stream stayed up",
    )
    check(not stopped.get("restore_errors"), "every link set down was set up again")
    check(
        abs(stopped.get("clock_delta_ns", CLOCK_LIMIT_NS)) < CLOCK_LIMIT_NS,
        "the wall clock and the monotonic clock of the lab host agree within 50 ms",
    )
    intervals = {e["interval_s"] for e in events if e["name"] == "stream_started"} or {
        INTERVAL_S
    }
    streams = [traffic.Stream(s.id, s.source, s.destination) for s in test.streams]
    try:
        measured = traffic.measure(pcaps, streams, windows, max(intervals))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        check(False, f"the captures can be decoded ({error})")
        return
    result["traffic"] = measured
    for ident, flow in measured["streams"].items():
        check(flow["cadence_ok"], f"stream {ident} sent a probe at least every 450 ms")
        check(
            not flow["capture_mismatches"],
            f"stream {ident} shows the same replies at both capture points",
        )
    base = traffic.baseline(measured, BASELINE)
    result["baseline"] = base
    for ident, counts in base["streams"].items():
        check(
            counts["ok"],
            f"stream {ident} delivered 30 probes or more in the baseline, none lost or duplicated",
        )
    for step in test.steps:
        window = measured["windows"][step.name]
        judged: dict[str, Any] = {}
        for expect in step.expect:
            for ident in expect.streams:
                counts = window["streams"][str(ident)]
                outage = counts["outage"]
                verdict, reason = judge(outage, expect.max_outage_s)
                if counts["duplicates"] and verdict != "fail":
                    verdict, reason = (
                        "fail",
                        f"{counts['duplicates']} duplicated probes",
                    )
                judged[str(ident)] = {
                    "limit_s": expect.max_outage_s,
                    "lower_s": outage["lower_s"] if outage else 0.0,
                    "upper_s": outage["upper_s"] if outage else 0.0,
                    "lost": counts["lost"],
                    "duplicates": counts["duplicates"],
                    "sent": counts["sent"],
                    "delivered": counts["delivered"],
                    "verdict": verdict,
                    "reason": reason,
                }
        verdict = rollup([s["verdict"] for s in judged.values()])
        result["steps"].append(
            {
                "name": step.name,
                "action": None
                if step.action is None
                else {"link": step.action.link, "state": step.action.state},
                "hold_s": step.hold_s,
                "start_s": window["start_s"],
                "end_s": window["end_s"],
                "verdict": verdict,
                "streams": judged,
            }
        )
        part(verdict, f"Step {step.name} is {verdict}.")


def timeline(folder: str | Path, result: Mapping[str, Any]) -> str:
    """A short TSV of the events and the outages, in time order."""
    events = _events(Path(folder) / EVENTS_FILE)
    measured = result.get("traffic")
    zero = measured["start_ns"] if measured else events[0]["epoch_ns"]
    rows = []
    for event in events:
        detail = {
            k: v for k, v in event.items() if k not in ("name", "epoch_ns", "mono_ns")
        }
        text = json.dumps(detail, sort_keys=True) if detail else ""
        rows.append(
            (event["epoch_ns"] - zero, "event", f"{event['name']} {text}".strip())
        )
    for ident, flow in (measured or {}).get("streams", {}).items():
        for gap in flow["gaps"]:
            upper = "?" if gap["upper_s"] is None else gap["upper_s"]
            where = ", ".join(gap["where"]) or "not sent"
            text = (
                f"lost {gap['lost']} probes, seq {gap['first_seq']} to "
                f"{gap['last_seq']}, outage {gap['lower_s']} to {upper} s, {where}"
            )
            rows.append((round(gap["begins_s"] * traffic.NS), f"stream {ident}", text))
    lines = ["time_s\twhat\tdetail"]
    lines += [
        f"{traffic.seconds(t):.6f}\t{what}\t{text}" for t, what, text in sorted(rows)
    ]
    return "\n".join(lines) + "\n"


def replay(folder: str | Path) -> tuple[dict[str, Any], bool]:
    """Compute result.json again from the saved files; also say if it equals the saved one."""
    folder = Path(folder)
    computed = evaluate(folder)
    try:
        saved = json.loads((folder / RESULT_FILE).read_text())
    except (OSError, ValueError) as error:
        msg = f"{folder / RESULT_FILE}: cannot read the saved result: {error}"
        raise LabTestError(msg) from None
    return computed, computed == saved
