# SPDX-License-Identifier: MIT
"""Results summary: a Markdown table and an SVG chart from saved `nw test` runs.

A summary file in the lab repository lists the labs as rows and the modes as
columns. Each cell names the run directories written by `nw test run --save`.
Every test folder in them counts for the cell. The summary rewrites the lines
between two markers in a Markdown file and writes the chart of the worst outage.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from network_toolkit import labtest

START = "<!-- results:start -->"
END = "<!-- results:end -->"
SPEC_FIELDS = (
    (
        "markdown",
        "chart",
        "chart_alt",
        "pass_icon",
        "fail_icon",
        "caption",
        "modes",
        "rows",
    ),
    (),
)
ROW_FIELDS = (("lab", "topology", "link"), ("label", "cells"))
CELL_FIELDS = (("runs",), ("link",))
NBSP = "&nbsp;"
EN_DASH = "\u2013"

# Chart geometry, in pixels, of the results chart in the lab README.
WIDTH = 830
AXIS_X = 300
AXIS_PX = 440
MIN_AXIS_S = 20
TICK_S = 5
TOP = 30
MODE_PX = 22
ROW_PAD = 16
CHAR_PX = 6.5
RIGHT_EDGE = 820
GREEN = "#1a7f37"
RED = "#cf222e"
MUTED = "#57606a"
FAINT = "#8c959f"


@dataclass(frozen=True)
class Outage:
    lower: float
    upper: float
    limit: float
    step: str
    source: str
    destination: str


@dataclass(frozen=True)
class Cell:
    verdict: str
    passed: int
    total: int
    errors: int
    worst: Outage | None
    intervals: frozenset[float]
    runs: tuple[Path, ...]
    link: Path | None


def _node(point: str) -> str:
    return point.split(":", 1)[0]


def _test(folder: Path) -> tuple[str, float, Outage | None]:
    """The verdict, ping interval and longest decided outage of one saved test."""
    path = folder / labtest.RESULT_FILE
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        labtest._fail(str(path), f"cannot read the result: {error}")
    worst: Outage | None = None
    try:
        verdict = result["verdict"]
        interval = float(result["traffic"]["interval_s"])
        if verdict == "error":
            return verdict, interval, None
        test = labtest.load_test(folder / labtest.TEST_FILE, folder / labtest.LAB_FILE)
        ends = {s.name: (s.source, s.destination) for s in test.streams}
        for step in result["steps"]:
            for name, stream in step["streams"].items():
                # The report gives these outages ERROR.
                if (
                    stream["verdict"] == "error"
                    or stream.get("diagnostic_only")
                    or stream["upper_s"] is None
                ):
                    continue
                if worst is None or stream["upper_s"] > worst.upper:
                    source, destination = ends[name]
                    worst = Outage(
                        stream["lower_s"],
                        stream["upper_s"],
                        stream["limit_s"],
                        step["name"],
                        _node(source),
                        _node(destination),
                    )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        labtest._fail(str(path), f"not a result of nw test run: {error!r}")
    return verdict, interval, worst


def _cell(raw: Any, base: Path, where: str) -> Cell | None:
    if raw is None:
        return None
    raw = labtest._fields(raw, where, CELL_FIELDS)
    runs = tuple(
        base / labtest._text(run, f"{where}: runs")
        for run in labtest._list(raw["runs"], f"{where}: runs")
    )
    link = labtest._optional_text(raw, "link", where)
    link_path = None if link is None else base / link
    counts: Counter[str] = Counter()
    worst: Outage | None = None
    intervals = set()
    seen: dict[str, Path] = {}
    for run in runs:
        if not run.is_dir():
            labtest._fail(str(run), "run directory is missing")
        if (run / labtest.TEST_FILE).is_file():
            tests = [run]
        else:
            tests = sorted(
                p for p in run.iterdir() if (p / labtest.TEST_FILE).is_file()
            )
        if not tests:
            labtest._fail(str(run), f"no test folder with {labtest.TEST_FILE}")
        for folder in tests:
            if folder.name in seen:
                labtest._fail(
                    where,
                    f"test {folder.name} is in both {seen[folder.name]} and {folder}",
                )
            seen[folder.name] = folder
            verdict, interval, outage = _test(folder)
            counts[verdict] += 1
            intervals.add(interval)
            if outage and (worst is None or outage.upper > worst.upper):
                worst = outage
    verdict = "FAIL" if counts["fail"] else "PASS" if counts["pass"] else "ERROR"
    return Cell(
        verdict,
        counts["pass"],
        counts.total(),
        counts["error"],
        worst,
        frozenset(intervals),
        runs,
        link_path,
    )


@dataclass(frozen=True)
class Row:
    lab: str
    topology: str
    label: str
    link: str
    cells: tuple[Cell | None, ...]


def _rel(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path, start)).as_posix()


def _seconds(value: float) -> str:
    return f"{value:.2f}"


def _passed(cell: Cell) -> str:
    text = f"{cell.passed}{NBSP}of{NBSP}{cell.total}"
    if cell.errors:
        text += f", {cell.errors}{NBSP}error{'s' if cell.errors > 1 else ''}"
    return text


def _table_cell(cell: Cell | None, icons: dict[str, str], here: Path) -> str:
    if cell is None:
        return "not run"
    count = _passed(cell)
    if cell.link:
        count = f"[{count}]({_rel(cell.link, here)})"
    if cell.verdict in icons:
        return f'![{cell.verdict}]({icons[cell.verdict]} "{cell.verdict}") {count}'
    return f"{cell.verdict} {count}"


def _worst_cell(cell: Cell | None) -> str:
    if cell is None or cell.worst is None:
        return "—"
    w = cell.worst
    return (
        f"{_seconds(w.lower)}{EN_DASH}{_seconds(w.upper)}{NBSP}s of{NBSP}{w.limit:g}{NBSP}s, "
        f"{labtest._cell(w.step)}, "
        f"{labtest._cell(w.source)}{NBSP}→{NBSP}{labtest._cell(w.destination)}"
    )


def _interval(cells: list[Cell]) -> str:
    values = sorted({i for c in cells for i in c.intervals})
    return " or ".join(f"{round(v * 1000):g}" for v in values)


def _markdown(
    spec: dict[str, Any],
    modes: list[str],
    rows: list[Row],
    here: Path,
    base: Path,
    spec_path: Path,
) -> list[str]:
    cells = [c for r in rows for c in r.cells if c is not None]
    icons = {
        "PASS": _rel(base / spec["pass_icon"], here),
        "FAIL": _rel(base / spec["fail_icon"], here),
    }
    chart = _rel(base / spec["chart"], here)
    header = ["Lab", "Topology", *modes, *(f"Worst outage, {m}" for m in modes)]
    lines = [
        f"![{spec['chart_alt']}]({chart})",
        "",
        f"{spec['caption']}, one ping every {_interval(cells)}{NBSP}ms per stream.",
        "",
        "| " + " | ".join(header) + " |",
        "|" + " --- |" * len(header),
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[{row.lab}]({_rel(base / row.link, here)})",
                    row.topology,
                    *(_table_cell(c, icons, here) for c in row.cells),
                    *(_worst_cell(c) for c in row.cells),
                ]
            )
            + " |"
        )
    source = _rel(spec_path, here)
    lines += [
        "",
        (
            f"The values are generated with `nw test summary {source}` from the"
            f" runs that [{source}]({source}) lists."
        ),
    ]
    return lines


def _num(value: float) -> str:
    return f"{round(value, 1):g}"


def _svg(modes: list[str], rows: list[Row]) -> str:
    outages = [c.worst for r in rows for c in r.cells if c is not None and c.worst]
    longest = max((s.upper for s in outages), default=0.0)
    # Keep the 20 s axis while the longest mark still fits beside it.
    axis_s = float(MIN_AXIS_S)
    if AXIS_X + AXIS_PX / MIN_AXIS_S * longest > RIGHT_EDGE - 6:
        axis_s = -(-longest // TICK_S) * TICK_S
    scale = AXIS_PX / axis_s
    limits = Counter(s.limit for s in outages)
    limit = min(limits, key=lambda v: (-limits[v], v)) if limits else 5.0
    row_px = ROW_PAD + MODE_PX * len(modes)
    bottom = TOP + row_px * len(rows)
    height = bottom + 42

    def x(seconds: float) -> float:
        return AXIS_X + scale * seconds

    ticks = [float(t * TICK_S) for t in range(int(axis_s // TICK_S) + 1)]
    out = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" font-family="-apple-system, BlinkMacSystemFont, '
            f'\'Segoe UI\', Helvetica, Arial, sans-serif" font-size="13" fill="#1f2328">'
        ),
        f'  <rect width="{WIDTH}" height="{height}" fill="#ffffff"/>',
        (
            f'  <text x="{AXIS_X}" y="16" font-size="12" fill="{MUTED}">Worst outage '
            f"in any test, seconds (upper bound, one ping every "
            f"{_interval([c for r in rows for c in r.cells if c])} ms)</text>"
        ),
        '  <g stroke="#d0d7de" stroke-width="1">',
    ]
    out += [
        f'    <line x1="{_num(x(t))}" y1="{TOP - 4}" x2="{_num(x(t))}" y2="{bottom}"/>'
        for t in ticks
        if t != limit
    ]
    out += [
        "  </g>",
        (
            f'  <line x1="{_num(x(limit))}" y1="{TOP - 4}" x2="{_num(x(limit))}" '
            f'y2="{bottom}" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="5 4"/>'
        ),
        f'  <g font-size="12" fill="{MUTED}" text-anchor="middle">',
    ]
    labels = [(t, f"{t:g}") for t in ticks if abs(t - limit) >= 2]
    labels[-1] = (labels[-1][0], f"{labels[-1][1]} s")
    labels.append((limit, f"{limit:g} s limit"))
    out += [
        f'    <text x="{_num(x(t))}" y="{bottom + 18}">{text}</text>'
        for t, text in sorted(labels)
    ]
    out += ["  </g>", '  <g stroke="#eaeef2" stroke-width="1">']
    out += [
        f'    <line x1="10" y1="{TOP + row_px * i}" x2="{RIGHT_EDGE}" y2="{TOP + row_px * i}"/>'
        for i in range(1, len(rows))
    ]
    out += ["  </g>", '  <g font-weight="600">']
    middle = 20 + MODE_PX * (len(modes) - 1) / 2 + 4
    out += [
        f'    <text x="10" y="{_num(TOP + row_px * i + middle)}">'
        f"{escape(r.label)}</text>"
        for i, r in enumerate(rows)
    ]
    out += ["  </g>", f'  <g font-size="12" fill="{MUTED}" text-anchor="end">']
    marks = []
    blanks = []
    for i, row in enumerate(rows):
        for j, (mode, cell) in enumerate(zip(modes, row.cells, strict=True)):
            y = TOP + row_px * i + 20 + MODE_PX * j
            out.append(f'    <text x="{AXIS_X - 12}" y="{y + 4}">{escape(mode)}</text>')
            if (
                cell is None
                or cell.worst is None
                or cell.verdict not in ("PASS", "FAIL")
            ):
                text = "not run" if cell is None else "no measured outage"
                blanks.append(
                    f'  <text x="{AXIS_X + 6}" y="{y + 4}" fill="{FAINT}" '
                    f'font-style="italic">{text}</text>'
                )
                continue
            outage = cell.worst
            cx = x(outage.upper)
            if cell.verdict == "PASS":
                marks.append(
                    f'  <circle cx="{_num(cx)}" cy="{y}" r="6" fill="{GREEN}" stroke="none"/>'
                )
            else:
                marks.append(
                    f'  <rect x="{_num(cx - 6)}" y="{y - 6}" width="12" height="12" '
                    f'fill="{RED}" stroke="none"/>'
                )
            text = f"{_seconds(outage.upper)} s"
            if outage.limit != limit:
                text += f" · limit {outage.limit:g} s"
            if cx + 12 + CHAR_PX * len(text) > RIGHT_EDGE:
                marks.append(
                    f'  <text x="{_num(cx - 12)}" y="{y + 4}" text-anchor="end">{text}</text>'
                )
            else:
                marks.append(f'  <text x="{_num(cx + 12)}" y="{y + 4}">{text}</text>')
    out += ["  </g>", '  <g stroke="#fff" stroke-width="4" paint-order="stroke">']
    out += [*marks, "  </g>", *blanks]
    legend = bottom + 36
    out += [
        f'  <g font-size="12" fill="{MUTED}">',
        (
            f'    <circle cx="306" cy="{legend - 4}" r="5" fill="{GREEN}"/>'
            f'<text x="316" y="{legend}">PASS</text>'
        ),
        (
            f'    <rect x="358" y="{legend - 10}" width="10" height="10" fill="{RED}"/>'
            f'<text x="374" y="{legend}">FAIL</text>'
        ),
        (
            f'    <text x="420" y="{legend}">Limit is {limit:g} s unless the label says '
            "otherwise.</text>"
        ),
        "  </g>",
        "</svg>",
    ]
    return "\n".join(out) + "\n"


def summarize(spec_path: str | Path) -> tuple[Path, Path]:
    """Rewrite the results section of the Markdown file and write the chart."""
    spec_path = Path(spec_path)
    base = spec_path.parent
    where = str(spec_path)
    spec = labtest._fields(labtest._read_yaml(spec_path), where, SPEC_FIELDS)
    modes = [
        labtest._text(m, f"{where}: modes")
        for m in labtest._list(spec["modes"], f"{where}: modes")
    ]
    rows = []
    for n, entry in enumerate(labtest._list(spec["rows"], f"{where}: rows"), 1):
        at = f"{where}: row {n}"
        raw = labtest._fields(entry, at, ROW_FIELDS)
        cells = raw.get("cells") or {}
        if unknown := set(cells) - set(modes):
            labtest._fail(at, f"unknown mode {', '.join(sorted(unknown))}")
        topology = labtest._text(raw["topology"], f"{at}: topology")
        rows.append(
            Row(
                labtest._text(raw["lab"], f"{at}: lab"),
                topology,
                labtest._optional_text(raw, "label", at) or topology.replace("`", ""),
                labtest._text(raw["link"], f"{at}: link"),
                tuple(_cell(cells.get(m), base, f"{at}: {m}") for m in modes),
            )
        )
    markdown = base / labtest._text(spec["markdown"], f"{where}: markdown")
    chart = base / labtest._text(spec["chart"], f"{where}: chart")
    try:
        text = markdown.read_text(encoding="utf-8")
    except OSError as error:
        labtest._fail(str(markdown), f"cannot read the file: {error}")
    lines = text.split("\n")
    if (
        lines.count(START) != 1
        or lines.count(END) != 1
        or lines.index(START) > lines.index(END)
    ):
        labtest._fail(
            str(markdown), f"needs one {START} line followed by one {END} line"
        )
    section = _markdown(spec, modes, rows, markdown.parent, base, spec_path)
    lines[lines.index(START) + 1 : lines.index(END)] = section
    markdown.write_text("\n".join(lines), encoding="utf-8")
    chart.write_text(_svg(modes, rows), encoding="utf-8")
    return markdown, chart
