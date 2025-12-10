"""Programmatic API for diffing configurations and commands."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.results_enhanced import ResultsManager
from network_toolkit.sequence_manager import SequenceManager


@dataclass
class DiffOptions:
    """Options for the diff operation."""

    targets: str
    subject: str
    config: NetworkConfig
    baseline: Path | None = None
    ignore_patterns: list[str] | None = None
    save_current: Path | None = None
    store_results: bool = False
    results_dir: str | None = None
    verbose: bool = False
    session_pool: dict[str, DeviceSession] | None = None


@dataclass
class DiffOutcome:
    """Result of a single text comparison."""

    changed: bool
    output: str


@dataclass
class DiffItemResult:
    """Result of a diff operation for a specific device and subject."""

    device: str
    subject: str
    outcome: DiffOutcome | None
    error: str | None = None


@dataclass
class DiffResult:
    """Overall result of the diff operation."""

    results: list[DiffItemResult]
    total_changed: int
    total_missing: int
    device_pair_diff: bool = False


def _sanitize_filename(text: str) -> str:
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", text).strip("_.")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _filter_lines(text: str, ignore_patterns: list[str]) -> list[str]:
    if not ignore_patterns:
        return text.splitlines(keepends=False)
    regexes = [re.compile(p) for p in ignore_patterns]
    lines: list[str] = []
    for line in text.splitlines(keepends=False):
        if any(r.search(line) for r in regexes):
            continue
        lines.append(line)
    return lines


def _make_unified_diff(
    a_lines: list[str], b_lines: list[str], a_label: str, b_label: str
) -> str:
    diff = difflib.unified_diff(a_lines, b_lines, fromfile=a_label, tofile=b_label)
    return "\n".join(diff)


@contextmanager
def _get_session(
    device_name: str,
    config: NetworkConfig,
    session_pool: dict[str, DeviceSession] | None = None,
) -> Iterator[DeviceSession]:
    if session_pool is not None:
        session = session_pool.get(device_name)
        if session is None:
            session = DeviceSession(device_name, config)
            session_pool[device_name] = session
        session.connect()
        yield session
    else:
        with DeviceSession(device_name, config) as session:
            yield session


def _diff_texts(
    *,
    baseline_text: str,
    current_text: str,
    baseline_label: str,
    current_label: str,
    ignore_patterns: list[str],
) -> DiffOutcome:
    a = _filter_lines(baseline_text, ignore_patterns)
    b = _filter_lines(current_text, ignore_patterns)
    out = _make_unified_diff(a, b, baseline_label, current_label)
    return DiffOutcome(changed=bool(out.strip()), output=out)


def _find_baseline_file_for_command(base_dir: Path, command: str) -> Path | None:
    stem = f"cmd_{_sanitize_filename(command)}"
    for ext in (".txt", ".log", ".out"):
        candidate = base_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def diff_targets(options: DiffOptions) -> DiffResult:
    """Execute the diff operation based on the provided options."""
    subj = options.subject.strip()
    is_config = subj.lower() == "config"
    is_command = subj.startswith("/")

    sm = SequenceManager(options.config)
    mode_label = "config" if is_config else ("command" if is_command else "sequence")
    cmd_ctx = f"diff_{options.targets}_{mode_label}_{_sanitize_filename(subj)}"

    # Initialize ResultsManager if needed (though we might not use it for storing diffs directly
    # in the same way as run/backup, the original code used it).
    # The original code used it to initialize the results directory structure.
    _ = ResultsManager(
        options.config,
        store_results=options.store_results,
        results_dir=options.results_dir,
        command_context=cmd_ctx,
    )

    # Resolve targets
    def resolve_targets(target_expr: str) -> tuple[list[str], list[str]]:
        requested = [t.strip() for t in target_expr.split(",") if t.strip()]
        devices: list[str] = []
        unknowns: list[str] = []

        def _add(name: str) -> None:
            if name not in devices:
                devices.append(name)

        for name in requested:
            if options.config.devices and name in options.config.devices:
                _add(name)
            elif options.config.device_groups and name in options.config.device_groups:
                for m in options.config.get_group_members(name):
                    _add(m)
            else:
                unknowns.append(name)
        return devices, unknowns

    devices, unknown = resolve_targets(options.targets)
    if unknown and not devices:
        msg = f"Target(s) not found: {', '.join(unknown)}"
        raise NetworkToolkitError(msg)

    # Helper to optionally save current fetches
    def _save_current_artifact(dev: str, name: str, text: str) -> None:
        if not options.save_current:
            return
        path = options.save_current
        if path.suffix:  # looks like a file path
            # For multi-artifact (sequence), append sanitized name
            if name:
                parent = path.parent / _sanitize_filename(dev)
                _write_text(parent / f"{_sanitize_filename(name)}.txt", text)
            else:
                _write_text(path, text)
        else:
            # Directory
            dst = path / _sanitize_filename(dev)
            _write_text(dst / (f"{_sanitize_filename(name) or 'config'}.txt"), text)

    results: list[DiffItemResult] = []
    total_changed = 0
    total_missing = 0

    # Device-to-device mode: exactly two devices and no baseline
    if options.baseline is None and len(devices) == 2:
        dev_a, dev_b = devices[0], devices[1]

        try:
            if is_config:
                with _get_session(dev_a, options.config, options.session_pool) as sa:
                    curr_a = sa.execute_command("/export compact")
                with _get_session(dev_b, options.config, options.session_pool) as sb:
                    curr_b = sb.execute_command("/export compact")

                _save_current_artifact(dev_a, "export_compact", curr_a)
                _save_current_artifact(dev_b, "export_compact", curr_b)

                outcome = _diff_texts(
                    baseline_text=curr_a,
                    current_text=curr_b,
                    baseline_label=f"{dev_a}:/export compact",
                    current_label=f"{dev_b}:/export compact",
                    ignore_patterns=options.ignore_patterns or [],
                )
                results.append(
                    DiffItemResult(
                        device=f"{dev_a} vs {dev_b}", subject="config", outcome=outcome
                    )
                )
                if outcome.changed:
                    total_changed += 1

            elif is_command:
                with _get_session(dev_a, options.config, options.session_pool) as sa:
                    curr_a = sa.execute_command(subj)
                with _get_session(dev_b, options.config, options.session_pool) as sb:
                    curr_b = sb.execute_command(subj)

                _save_current_artifact(dev_a, subj, curr_a)
                _save_current_artifact(dev_b, subj, curr_b)

                outcome = _diff_texts(
                    baseline_text=curr_a,
                    current_text=curr_b,
                    baseline_label=f"{dev_a}:{subj}",
                    current_label=f"{dev_b}:{subj}",
                    ignore_patterns=options.ignore_patterns or [],
                )
                results.append(
                    DiffItemResult(
                        device=f"{dev_a} vs {dev_b}", subject=subj, outcome=outcome
                    )
                )
                if outcome.changed:
                    total_changed += 1
            else:
                msg = (
                    "Device-to-device diff only supports 'config' or a single command."
                )
                raise NetworkToolkitError(msg)

            return DiffResult(
                results=results,
                total_changed=total_changed,
                total_missing=total_missing,
                device_pair_diff=True,
            )

        except Exception as e:
            results.append(
                DiffItemResult(
                    device=f"{dev_a} vs {dev_b}",
                    subject=subj,
                    outcome=None,
                    error=str(e),
                )
            )
            return DiffResult(
                results=results,
                total_changed=total_changed,
                total_missing=total_missing,
                device_pair_diff=True,
            )

    # Standard mode: diff against baseline
    if not options.baseline:
        msg = "Baseline path is required (unless comparing exactly two devices)."
        raise NetworkToolkitError(msg)

    if not options.baseline.exists():
        msg = f"Baseline path not found: {options.baseline}"
        raise NetworkToolkitError(msg)

    for dev in devices:
        try:
            if is_config:
                # Diff config vs file
                if options.baseline.is_dir():
                    # Try to find file in dir
                    cand = options.baseline / f"{dev}.rsc"
                    if not cand.exists():
                        cand = options.baseline / f"{dev}.txt"
                    if not cand.exists():
                        # Try finding any file with device name
                        matches = list(options.baseline.glob(f"*{dev}*"))
                        if matches:
                            cand = matches[0]
                    base_file = cand
                else:
                    base_file = options.baseline

                if not base_file.exists():
                    results.append(
                        DiffItemResult(
                            device=dev,
                            subject="config",
                            outcome=None,
                            error=f"Baseline file not found: {base_file}",
                        )
                    )
                    total_missing += 1
                    continue

                base_text = _read_text(base_file)
                with _get_session(dev, options.config, options.session_pool) as s:
                    curr_text = s.execute_command("/export compact")

                _save_current_artifact(dev, "export_compact", curr_text)

                outcome = _diff_texts(
                    baseline_text=base_text,
                    current_text=curr_text,
                    baseline_label=str(base_file),
                    current_label=f"{dev}:/export compact",
                    ignore_patterns=options.ignore_patterns or [],
                )
                results.append(
                    DiffItemResult(device=dev, subject="config", outcome=outcome)
                )
                if outcome.changed:
                    total_changed += 1

            elif is_command:
                # Diff command vs file
                cmd_base_file: Path | None
                if options.baseline.is_dir():
                    cmd_base_file = _find_baseline_file_for_command(
                        options.baseline, subj
                    )
                else:
                    cmd_base_file = options.baseline

                if not cmd_base_file or not cmd_base_file.exists():
                    results.append(
                        DiffItemResult(
                            device=dev,
                            subject=subj,
                            outcome=None,
                            error=f"Baseline file not found for command: {subj}",
                        )
                    )
                    total_missing += 1
                    continue

                base_text = _read_text(cmd_base_file)
                with _get_session(dev, options.config, options.session_pool) as s:
                    curr_text = s.execute_command(subj)

                _save_current_artifact(dev, subj, curr_text)

                outcome = _diff_texts(
                    baseline_text=base_text,
                    current_text=curr_text,
                    baseline_label=str(cmd_base_file),
                    current_label=f"{dev}:{subj}",
                    ignore_patterns=options.ignore_patterns or [],
                )
                results.append(
                    DiffItemResult(device=dev, subject=subj, outcome=outcome)
                )
                if outcome.changed:
                    total_changed += 1

            else:
                # Sequence diff
                if not options.baseline.is_dir():
                    msg = "For sequence diff, baseline must be a directory."
                    raise NetworkToolkitError(msg)

                seq_cmds = sm.resolve(dev, subj)
                if not seq_cmds:
                    results.append(
                        DiffItemResult(
                            device=dev,
                            subject=subj,
                            outcome=None,
                            error=f"Sequence '{subj}' empty or not found for {dev}",
                        )
                    )
                    continue

                with _get_session(dev, options.config, options.session_pool) as s:
                    for cmd in seq_cmds:
                        seq_base_file: Path | None = _find_baseline_file_for_command(
                            options.baseline, cmd
                        )
                        if not seq_base_file:
                            results.append(
                                DiffItemResult(
                                    device=dev,
                                    subject=cmd,
                                    outcome=None,
                                    error="Baseline file missing",
                                )
                            )
                            total_missing += 1
                            continue

                        base_text = _read_text(seq_base_file)
                        curr_text = s.execute_command(cmd)
                        _save_current_artifact(dev, cmd, curr_text)

                        outcome = _diff_texts(
                            baseline_text=base_text,
                            current_text=curr_text,
                            baseline_label=str(seq_base_file),
                            current_label=f"{dev}:{cmd}",
                            ignore_patterns=options.ignore_patterns or [],
                        )
                        results.append(
                            DiffItemResult(device=dev, subject=cmd, outcome=outcome)
                        )
                        if outcome.changed:
                            total_changed += 1

        except Exception as e:
            results.append(
                DiffItemResult(device=dev, subject=subj, outcome=None, error=str(e))
            )

    return DiffResult(
        results=results,
        total_changed=total_changed,
        total_missing=total_missing,
        device_pair_diff=False,
    )
