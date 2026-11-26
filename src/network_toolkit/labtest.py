# SPDX-License-Identifier: MIT
"""Lab tests: a test file, its fixed flow in a containerlab lab, the verdict and replay.

A lab file holds what all tests of one lab share: the state statements, the
ping streams and the file the switch logs arrive in. A test file names its lab
file and holds ordered steps. A step sets one cable down or up, holds for a
time, limits the outage of every stream and can carry log rules. The flow
checks the state, starts captures and streams, checks a quiet window, runs the
steps, checks the state again and stops.

The verdict is computed from the saved evidence only. `replay` therefore
computes the same `result.json` and `report.md` again without the lab.
"""

from __future__ import annotations

import html
import importlib
import json
import math
import re
import subprocess
import time
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, NoReturn

import yaml

from network_toolkit import intent, lab, lab_reboot, traffic
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.intent import IntentItem, Verdict

if TYPE_CHECKING:
    from network_toolkit.client import NetworkaClient

TEST_FILE = "test.yaml"
LAB_FILE = "lab.yaml"
EVENTS_FILE = "events.jsonl"
SYSLOG_FILE = "syslog.log"
RESULT_FILE = "result.json"
REPORT_FILE = "report.md"
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
# Check the collector twice per ping interval to see late switch messages promptly.
LOG_POLL_S = traffic.INTERVAL_NS / (2 * NS)
QUIET = "quiet window"
CLOSING = "after the steps"
EVERY = "every"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

TEST_FIELDS = (("name", "purpose", "lab", "steps"), ("source", "log"))
LAB_FIELDS = (("state", "streams"), ("switch_log",))
STREAM_FIELDS = (("name", "from", "to"), ())
STEP_FIELDS = (
    ("name", "hold_s", "max_outage_s", "expected"),
    ("cable", "state", "action", "wait_healthy_s", "log"),
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
class Cable:
    cable: str
    state: str


@dataclass(frozen=True)
class Reboot:
    switch: str
    wait_s: float


@dataclass(frozen=True)
class Step:
    name: str
    action: Cable | Reboot
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
    raw: str

    def is_marker(self, text: str) -> bool:
        return self.text in (text, f"script,info {text}")


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


def _action(entry: Mapping[str, Any], where: str) -> Cable | Reboot:
    if "action" in entry:
        if "cable" in entry or "state" in entry:
            _fail(where, "choose one reboot or cable action")
        action = _fields(entry["action"], f"{where}: action", (("reboot",), ()))
        wait = _seconds(entry.get("wait_healthy_s"), f"{where}: wait_healthy_s")
        if not wait:
            _fail(where, "a reboot needs a positive wait_healthy_s")
        return Reboot(_text(action["reboot"], f"{where}: reboot"), wait)
    if "wait_healthy_s" in entry or entry.get("state") not in ("down", "up"):
        _fail(where, "a cable action needs a state of down or up")
    return Cable(_point(entry.get("cable"), f"{where}: cable"), entry["state"])


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
        if step_name in (QUIET, CLOSING) or step_name in (s.name for s in steps):
            _fail(f"{where}: name", f"{step_name!r} is taken")
        limits = entry["max_outage_s"]
        if not isinstance(limits, dict) or sorted(limits) != sorted(names):
            _fail(
                f"{where}: max_outage_s",
                f"must give a limit for each stream of {lab_path}: {', '.join(names)}",
            )
        steps.append(
            Step(
                step_name,
                _action(entry, where),
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


def judge(
    outage: Mapping[str, Any] | None, limit: float, *, summary: str | None = None
) -> tuple[Verdict, str]:
    """The verdict of one stream's outage in one step against its limit.

    A 0 s limit allows no lost and no late ping. Otherwise pass when the upper
    bound is at most the limit, and fail when the lower bound is above it. A
    lost ping makes the outage longer than its lower bound, so a lower bound
    equal to the limit also fails. Bounds that straddle the limit cannot
    decide, which is error.
    """
    if outage is None:
        return "pass", summary or traffic.lost_text(0, None, None)
    lower, upper = outage["lower_s"], outage["upper_s"]
    text = summary or traffic.lost_text(outage["lost"], lower, upper)
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
            LogLine(
                (when - epoch) // timedelta(microseconds=1) * 1000, switch, message, raw
            )
        )
    return lines


def _fill_hosts(client: NetworkaClient, the_lab: lab.Lab) -> None:
    """Give each inventory device without a host the management address of its lab node."""
    for name, node in the_lab.nodes.items():
        device = client.devices.get(name)
        if device is not None and not device.host:
            device.host = node.address


def _switches(client: NetworkaClient, the_lab: lab.Lab, test: LabTest) -> list[str]:
    """Lab switches with marker support, or identified by inventory or log rules."""
    rules = [*test.log, *(rule for step in test.steps for rule in step.log)]
    found = {rule.switch for rule in rules if rule.switch != EVERY}
    if "switches" in client.groups:
        found.update(
            set(client.config.get_group_members("switches")) & the_lab.nodes.keys()
        )
    for name in the_lab.nodes:
        device = client.devices.get(name)
        module = intent.PLATFORMS.get(device.device_type) if device else None
        if module and hasattr(importlib.import_module(module), "log_marker"):
            found.add(name)
    return sorted(found)


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
        if switch not in session.lab.nodes or switch not in client.devices:
            errors[switch] = "not a device of this lab"
            continue
        try:
            module = intent.platform(client.devices[switch].device_type)
            if not hasattr(module, "log_marker"):
                errors[switch] = "platform has no log marker"
            elif error := module.log_marker(client, switch, text, **run_options):
                errors[switch] = error
        except Exception as error:
            errors[switch] = str(error) or type(error).__name__
    session.mark(
        "log_marker", which=which, text=text, switches=list(switches), errors=errors
    )


def _added(path: Path, offset: int) -> bytes | None:
    """What was added to the switch log since `offset`, or None without the file."""
    if not path.is_file():
        return None
    data = path.read_bytes()
    return data[offset:] if len(data) >= offset else data


def _wait_for_repair_logs(
    session: lab.Session, test: LabTest, switches: list[str], path: Path, offset: int
) -> None:
    """Wait for the restored cable's normal up indications before ending its log."""
    for end, started in session.repairs.items():
        ends = {str(end), str(session.lab.peer(end))}
        up = next(
            (
                s
                for s in test.steps
                if isinstance(s.action, Cable)
                and s.action.state == "up"
                and s.action.cable in ends
            ),
            None,
        )
        pending = {
            (switch, rule.text)
            for rule in (up.log if up else ())
            if rule.kind == "must"
            for switch in (switches if rule.switch == EVERY else [rule.switch])
        }
        if not pending or up is None:
            session.mark(
                "repair_log",
                point=str(end),
                detail="no required switch log line for this repair",
            )
            continue
        # The up step's hold is the test author's allowed time for its switch log.
        deadline = time.monotonic() + up.hold_s
        while True:
            lines = parse_log((_added(path, offset) or b"").decode(errors="replace"))
            pending = {
                (switch, text)
                for switch, text in pending
                if not any(
                    line.epoch_ns >= started
                    and line.switch == switch
                    and text.casefold() in line.text.casefold()
                    for line in lines
                )
            }
            if not pending or time.monotonic() >= deadline:
                break
            time.sleep(LOG_POLL_S)
        if pending:
            rows = ", ".join(f"{switch} {text!r}" for switch, text in sorted(pending))
            session.mark("run_error", reason=f"Missing repair log for {end}: {rows}.")
        else:
            session.mark(
                "repair_log",
                point=str(end),
                detail="switch confirmed the repair in its log",
            )


def _save_log(
    path: Path, offset: int, folder: Path, switches: list[str], end: str
) -> None:
    """Wait for the end markers, including when the collector creates its first file."""
    deadline = time.monotonic() + MARKER_WAIT_S
    while True:
        added = _added(path, offset)
        if added is not None:
            seen = {
                line.switch
                for line in parse_log(added.decode(errors="replace"))
                if line.is_marker(end)
            }
            if seen >= set(switches):
                break
        if time.monotonic() >= deadline:
            break
        time.sleep(LOG_POLL_S)
    if added is not None:
        (folder / SYSLOG_FILE).write_bytes(added)


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
        if isinstance(step.action, Cable)
        for end in (
            lab.point(step.action.cable),
            the_lab.peer(lab.point(step.action.cable)),
        )
    }
    _fill_hosts(client, the_lab)
    for step in test.steps:
        if isinstance(step.action, Reboot):
            lab_reboot.validate_target(client, the_lab, step.action.switch)
    switches = _switches(client, the_lab, test) if test.switch_log else []
    if test.switch_log and not switches:
        msg = f"lab {the_lab.name} has no device that can write a log marker"
        raise LabTestError(msg)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / TEST_FILE).write_text(test.text, encoding="utf-8")
    (folder / LAB_FILE).write_text(test.lab_text, encoding="utf-8")
    items = test.items()
    log_path = lab_dir / test.switch_log if test.switch_log else None
    session = lab.Session(the_lab, folder)
    interrupted: BaseException | None = None

    @contextmanager
    def record_errors() -> Iterator[None]:
        nonlocal interrupted
        try:
            yield
        except BaseException as error:
            session.mark("run_error", reason=str(error) or type(error).__name__)
            if not isinstance(error, Exception):
                interrupted = error

    offset = 0
    session.mark("test_started", test=test.name, lab=the_lab.name)
    with record_errors(), session:
        if log_path is not None:
            if log_path.is_file():
                offset = log_path.stat().st_size
            _markers(
                client, session, switches, marker(test, "start"), "start", run_options
            )
        before = intent.run_intent(
            client, items, folder / "state-before", **run_options
        )
        session.mark("state_checked", when="before", verdict=before.verdict)
        if before.verdict == "pass":
            _flow(client, test, session, items, sorted(cables), run_options)
    if session.stopped is None:
        # An interrupt during cleanup can leave a sender, capture or cable outstanding.
        with record_errors():
            session.stop()
    if log_path is not None:
        end = marker(test, "end")
        with record_errors():
            _wait_for_repair_logs(session, test, switches, log_path, offset)
        with record_errors():
            _markers(client, session, switches, end, "end", run_options)
        with record_errors():
            _save_log(log_path, offset, folder, switches, end)
    result = evaluate(folder)
    (folder / RESULT_FILE).write_bytes(result_bytes(result))
    (folder / REPORT_FILE).write_text(report(folder, result), encoding="utf-8")
    if interrupted is not None:
        raise interrupted
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
        # A new request can yield another first reply once per ping interval.
        time.sleep(traffic.INTERVAL_NS / NS)


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
    for number, step in enumerate(test.steps, 1):
        session.mark("step_start", step=step.name)
        action = step.action
        if isinstance(action, Cable):
            session.set_link(action.cable, action.state)
        else:
            lab_reboot.run(
                client,
                session,
                action.switch,
                number,
                action.wait_s,
                items,
                run_options,
            )
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

    lines: list[LogLine]  # Device messages, with the engine's markers removed.
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
    lines = parse_log((folder / SYSLOG_FILE).read_text(errors="replace"))
    expected = set(starts[0]["switches"])
    unknown = {line.switch for line in lines} - expected
    if unknown:
        part(
            "error",
            f"The collector recorded unverified senders: {', '.join(sorted(unknown))}.",
        )
    switches = sorted(expected | unknown)
    for event in [*starts, *ends]:
        for switch, error in event["errors"].items():
            part(
                "error",
                f"{switch} could not write the {event['which']} marker: {error}.",
            )
    texts = {"start": starts[0]["text"], "end": ends[0]["text"] if ends else None}
    markers: dict[str, dict[str, int | None]] = {}
    for switch in switches:
        markers[switch] = {
            which: next(
                (
                    line.epoch_ns
                    for line in lines
                    if text and line.switch == switch and line.is_marker(text)
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
        first, last = markers[switch]["start"], markers[switch]["end"]
        if first is not None and last is not None and last < first:
            part("error", f"{switch} logged its end marker before its start.")
    spans = {
        s: (m["start"], m["end"])
        for s, m in markers.items()
        if s in expected
        and m["start"] is not None
        and m["end"] is not None
        and m["start"] <= m["end"]
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
    messages = [
        line
        for line in lines
        if not any(text and line.is_marker(text) for text in texts.values())
    ]
    return SwitchLog(messages, switches, spans), summary


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
    for event in events:
        if event["name"] == "run_error":
            part("error", f"The run stopped: {event['reason']}")
    if marks.get("quiet_checked", {}).get("problems"):
        problems = "; ".join(marks["quiet_checked"]["problems"])
        part(
            "error",
            f"The quiet window was not clean, so no cable was changed: {problems}",
        )
    reboots: dict[str, Any] = {}
    for n, step in enumerate(test.steps, 1):
        if isinstance(step.action, Reboot) and any(
            e["name"] == "step_start" and e["step"] == step.name for e in events
        ):
            action = step.action
            proof = lab_reboot.proof(
                folder, events, action.switch, n, action.wait_s, test.items()
            )
            reboots[step.name] = proof
            part(
                proof["verdict"],
                f"Reboot of {action.switch}: {proof.get('reason', proof['verdict'])}",
            )
    if reboots:
        result["reboots"] = reboots
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
    result["verdict"] = "error" if "run_error" in marks else rollup(parts)
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
    if cutoff := marks.get("stream_cutoff"):
        windows.append(traffic.Window(CLOSING, edges[-1], cutoff["epoch_ns"]))
    pcaps = {
        e["point"]: folder / e["pcap"] for e in events if e["name"] == "capture_started"
    }
    for where in sorted(test.ends()):
        pcap = pcaps.get(where)
        if pcap is None:
            check(False, f"capture at {where} started")
            continue
        found = traffic.check_capture(pcap, pcap.with_suffix(".log"))
        detail = f"capture at {where} is complete and dropped no packet"
        if not found["valid"]:
            detail += f" (file present: {found['present']}, kernel drops: {found['kernel_dropped']})"
        check(found["valid"], detail)
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
    if not cutoff:
        # Legacy runs used this wording in result.json, which replay compares exactly.
        for window in measured["windows"].values():
            for counts in window["streams"].values():
                if counts["outage"] is None:
                    counts["summary"] = (
                        f"no ping lost at one ping every {traffic.INTERVAL_NS // 1_000_000} ms"
                    )
    else:
        for window in measured["windows"].values():
            for counts in window["streams"].values():
                if outage := counts["outage"]:
                    lost = counts["lost"]
                    pings = "ping" if lost == 1 else "pings"
                    counts["summary"] = (
                        f"{lost} {pings} lost in total at one ping every "
                        f"{traffic.INTERVAL_NS // 1_000_000} ms, longest measured stop "
                        f"{_stop_text(outage['lower_s'], outage['upper_s'])}"
                    )
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
    if cutoff:
        closing = traffic.quiet(measured, CLOSING)
        result["closing"] = closing
        verdicts: list[Verdict] = []
        for name, counts in closing["streams"].items():
            if counts["ok"]:
                continue
            if counts["lost"] or counts["duplicates"]:
                verdicts.append("fail")
                part(
                    "fail",
                    f"After the steps, {name}: {counts['summary']}, {counts['duplicates']} duplicated.",
                )
            else:
                verdicts.append("error")
                part(
                    "error", f"After the steps, {name} had insufficient ping evidence."
                )
        closing["verdict"] = rollup(verdicts)
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
            summary = counts["summary"] if outage is None or cutoff else None
            verdict, reason = judge(outage, limit, summary=summary)
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
        spans = (
            {
                switch: span
                for switch, (begin, end) in log.spans.items()
                if begin <= span[0] and span[1] <= end
            }
            if log
            else {}
        )
        rules = _judge_rules(step.log, log, spans, zero) if log else []
        verdicts = [s["verdict"] for s in streams.values()] + [
            r["verdict"] for r in rules
        ]
        if isinstance(step.action, Reboot):
            verdicts.append(result["reboots"][step.name]["verdict"])
        verdict = rollup(verdicts)
        result["steps"].append(
            {
                "name": step.name,
                "expected": step.expected,
                **(
                    {"cable": step.action.cable, "state": step.action.state}
                    if isinstance(step.action, Cable)
                    else {"reboot": step.action.switch}
                ),
                "hold_s": step.hold_s,
                "start_s": window["start_s"],
                "end_s": window["end_s"],
                "verdict": verdict,
                "streams": streams,
                "log": rules,
            }
        )
        part(verdict, f"Step {step.name} is {verdict}.")
    if cutoff:
        # Window measurements live alongside their verdicts in quiet, closing and steps.
        del measured["windows"]
        for step_result in result["steps"]:
            for counts in step_result["streams"].values():
                del counts["interval_s"]
        for flow in measured["streams"].values():
            del flow["interval_s"]
            flow["outages"] = flow.pop("gaps")
            for outage in flow["outages"]:
                if not_sent := outage.pop("absent_at_source"):
                    outage["not_sent"] = not_sent


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
    if name == "reboot_start":
        return "reboot", f"dispatching the reboot to {event['switch']}"
    if name == "reboot_command":
        return (
            "reboot",
            f"{event['switch']} command returned: {event['reply']['error'] or 'accepted'}",
        )
    if name == "reboot_health":
        return (
            "recovery",
            f"full lab state after reboot of {event['switch']}: {event['verdict']}",
        )
    if name == "stream_cutoff":
        return "streams", "measurement ended; captures wait for final replies"
    if name == "repair_start":
        return "cable", f"repairing {event['point']}"
    if name == "repair_log":
        return "cable", f"{event['point']}: {event['detail']}"
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


def _stop_text(lower: float, upper: float | None) -> str:
    if upper is None:
        return f"at least {lower:g} s"
    if lower == upper:
        return f"{lower:g} s"
    return f"{lower:g} to {upper:g} s"


def _cell(value: object) -> str:
    """Render untrusted YAML and syslog text as literal Markdown table content."""
    value = html.escape(str(value), quote=False)
    value = re.sub(r"([\\|`*_\[\]~])", r"\\\1", value)
    return "<br>".join(value.splitlines()) or "—"


def _row(*cells: object) -> str:
    return "| " + " | ".join(_cell(cell) for cell in cells) + " |"


def report(folder: Path, result: Mapping[str, Any]) -> str:
    """Render verdicts, evidence for the log rules and the sequence of events."""
    test = load_test(folder / TEST_FILE, folder / LAB_FILE)
    events = _events(folder / EVENTS_FILE)
    zero = _zero(events)
    log_lines = (
        parse_log((folder / SYSLOG_FILE).read_text(errors="replace"))
        if (folder / SYSLOG_FILE).is_file()
        else []
    )
    output = [
        f"# {result['verdict'].upper()} — {_cell(test.name)}",
        "",
        _cell(test.purpose),
    ]
    if result["reasons"]:
        output += ["", *[f"- {_cell(reason)}" for reason in result["reasons"]]]
    measured_steps = {s["name"]: s for s in result["steps"]}
    output += _report_traffic(test, result, measured_steps)
    output += _report_rules(test, result, measured_steps, log_lines, zero)
    output += _report_events(result, events, log_lines, zero)
    return "\n".join(output) + "\n"


def _report_traffic(
    test: LabTest, result: Mapping[str, Any], measured_steps: dict[str, Any]
) -> list[str]:
    output = [
        "",
        "## Traffic",
        "",
        "| Step | Stream | Limit | Total lost pings | Longest measured stop | Verdict |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    points = {s.name: f"{s.source} → {s.destination}" for s in test.streams}
    for step in test.steps:
        measured = measured_steps.get(step.name, {})
        for name, limit in step.limits:
            counts = measured.get("streams", {}).get(name)
            if counts is None:
                output.append(
                    _row(
                        step.name,
                        points[name],
                        f"{limit:g} s",
                        "unmeasured",
                        "unmeasured",
                        "unverified",
                    )
                )
                continue
            lower, upper = counts["lower_s"], counts["upper_s"]
            output.append(
                _row(
                    step.name,
                    points[name],
                    f"{limit:g} s",
                    f"{counts['lost']} at one ping every {traffic.INTERVAL_NS // 1_000_000} ms",
                    _stop_text(lower, upper),
                    counts["verdict"],
                )
            )
    for when in ("quiet", "closing"):
        if window := result.get(when):
            output += [
                "",
                f"**{_cell(window['window'])}** · {_cell(window['verdict'])}",
                "",
            ]
            for name, counts in window["streams"].items():
                output.append(
                    f"- {_cell(points[name])} · {_cell(counts['summary'])} · {_cell(counts['duplicates'])} duplicates"
                )
    for step_name, reboot in result.get("reboots", {}).items():
        output += [
            "",
            f"## Reboot of {_cell(reboot['switch'])}",
            "",
            f"{_cell(step_name)} · {_cell(reboot['verdict'])}",
            "",
        ]
        if "after_uptime_s" in reboot:
            output.append(
                f"- Uptime before dispatch was {reboot['before_uptime_s']:g} s. The switch reported {reboot['after_uptime_s']:g} s at +{reboot['elapsed_s']:g} s."
            )
        if "healthy_s" in reboot:
            output.append(
                f"- Full lab state was {_cell(reboot['state'])} at +{reboot['healthy_s']:g} s, against a {reboot['limit_s']:g} s limit."
            )
        if "reason" in reboot:
            output.append(f"- {_cell(reboot['reason'])}")
    return output


def _report_rules(
    test: LabTest,
    result: Mapping[str, Any],
    measured_steps: dict[str, Any],
    log_lines: list[LogLine],
    zero: int,
) -> list[str]:
    output = ["", "## Switch log rules", ""]
    raw = {
        (line.switch, traffic.seconds(line.epoch_ns - zero), line.text): line.raw
        for line in log_lines
    }
    markers = (result.get("switch_log") or {}).get("markers", {})
    groups: list[tuple[str, tuple[Rule, ...], list, dict | None]] = [
        ("Whole test", test.log, result.get("log", []), None)
    ]
    for step in test.steps:
        measured = measured_steps.get(step.name, {})
        groups.append((step.name, step.log, measured.get("log", []), measured))
    if not any(rules for _, rules, _, _ in groups):
        output.append("This test declares no switch log rules.")
    else:
        output += [
            "| Scope | Switch | Rule | Verdict | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    for scope, rules, judged, step_result in groups:
        for i, rule in enumerate(rules):
            item = judged[i] if i < len(judged) else {}
            targets = sorted(markers) if rule.switch == EVERY else [rule.switch]
            spans = []
            for target in targets:
                if step_result is not None:
                    bounds = (step_result.get("start_s"), step_result.get("end_s"))
                else:
                    bounds = (
                        markers.get(target, {}).get("start"),
                        markers.get(target, {}).get("end"),
                    )
                spans.append(
                    f"{target} {bounds[0]:g} to {bounds[1]:g} s"
                    if None not in bounds
                    else f"{target} unproven"
                )
            matches = [
                raw.get((hit["switch"], hit["time_s"], hit["text"]), hit["text"])
                for hit in item.get("lines", [])
            ]
            if not matches or item["verdict"] != "pass":
                matches.insert(0, item.get("reason", "unverified"))
            output.append(
                _row(
                    scope,
                    ", ".join(spans) or rule.switch,
                    f"{rule.kind} {rule.text}",
                    item.get("verdict", "unverified"),
                    "\n".join(matches),
                )
            )
    return output


def _report_events(
    result: Mapping[str, Any],
    events: list[dict[str, Any]],
    log_lines: list[LogLine],
    zero: int,
) -> list[str]:
    output = [
        "",
        "## What happened",
        "",
        "Times are relative to the start of the quiet window or, if it never started, the first recorded event.",
        "",
        "| Time (s) | Event | Detail |",
        "| --- | --- | --- |",
    ]
    rows = []
    for event in events:
        if (row := _event_row(event)) is not None:
            rows.append((event["epoch_ns"] - zero, *row))
        if event["name"] == "state_checked":
            state = result["state"].get(event["when"]) or {}
            for statement in state.get("statements", []):
                rows.append(
                    (
                        event["epoch_ns"] - zero,
                        "state",
                        f"{statement['statement']} {statement['verdict']}",
                    )
                )
    if not any(e["name"] == "stream_cutoff" for e in events):
        for e in events:
            if e["name"] == "steps_end":
                rows.append(
                    (
                        e["epoch_ns"] - zero,
                        "coverage",
                        "This run recorded no stream cutoff; traffic after the steps was not judged.",
                    )
                )
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
        for gap in flow.get("outages", flow.get("gaps", ())):
            where = ", ".join(gap["where"]) or "not sent"
            rows.append(
                (round(gap["begins_s"] * NS), name, f"{gap['summary']}, {where}")
            )
    for line in log_lines:
        rows.append((line.epoch_ns - zero, f"{line.switch} log", line.text))
    output.extend(
        _row(f"{t / NS:.3f}", what, detail)
        for t, what, detail in sorted(rows, key=lambda row: row[0])
    )
    return output


def result_bytes(result: Mapping[str, Any]) -> bytes:
    return (json.dumps(result, indent=2) + "\n").encode("utf-8")


def replay(folder: str | Path) -> tuple[dict[str, Any], bool]:
    """Rebuild result.json and report.md from the original evidence.

    Also say if the result equals the saved result.json.
    """
    folder = Path(folder)
    computed = evaluate(folder)
    try:
        saved = (folder / RESULT_FILE).read_bytes()
    except OSError as error:
        msg = f"{folder / RESULT_FILE}: cannot read the saved result: {error}"
        raise LabTestError(msg) from None
    (folder / REPORT_FILE).write_text(report(folder, computed), encoding="utf-8")
    return computed, result_bytes(computed) == saved
