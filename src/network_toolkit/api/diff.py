"""Programmatic API for diffing configurations and commands."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from network_toolkit.api.execution import execute_parallel
from network_toolkit.api.state_diff import StateDiffer
from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import resolve_named_targets
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
    heuristic: bool = False


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
    heuristic: bool = False,
) -> DiffOutcome:
    if heuristic:
        differ = StateDiffer()
        # Note: ignore_patterns are handled inside StateDiffer via canonicalization
        # but we might want to support user-supplied patterns too.
        # For now, StateDiffer uses its built-in patterns + IGNORE_PATTERNS.
        # If user supplied ignore_patterns, we could potentially add them to StateDiffer
        # but StateDiffer design currently relies on hardcoded patterns.
        # We will apply user ignore patterns as a pre-filter if provided.
        if ignore_patterns:
            baseline_text = "\n".join(_filter_lines(baseline_text, ignore_patterns))
            current_text = "\n".join(_filter_lines(current_text, ignore_patterns))

        result = differ.diff(baseline_text, current_text)
        out = result.to_string()
        return DiffOutcome(
            changed=bool(out.strip() and "No significant" not in out), output=out
        )

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


def _save_artifact(device: str, name: str, text: str, save_path: Path | None) -> None:
    if not save_path:
        return
    if save_path.suffix:  # looks like a file path
        # For multi-artifact (sequence), append sanitized name
        if name:
            parent = save_path.parent / _sanitize_filename(device)
            _write_text(parent / f"{_sanitize_filename(name)}.txt", text)
        else:
            _write_text(save_path, text)
    else:
        # Directory
        dst = save_path / _sanitize_filename(device)
        _write_text(dst / (f"{_sanitize_filename(name) or 'config'}.txt"), text)


def _perform_device_diff(
    device: str, options: DiffOptions, sequence_manager: SequenceManager
) -> list[DiffItemResult]:
    if options.baseline is None:
        return [
            DiffItemResult(
                device=device,
                subject=options.subject,
                outcome=None,
                error="Baseline is required for single-device diff.",
            )
        ]

    results: list[DiffItemResult] = []
    subj = options.subject.strip()
    is_config = subj.lower() == "config"
    is_command = subj.startswith("/")

    try:
        if is_config:
            # Diff config vs file
            if options.baseline.is_dir():
                # Try to find file in dir
                cand = options.baseline / f"{device}.rsc"
                if not cand.exists():
                    cand = options.baseline / f"{device}.txt"
                if not cand.exists():
                    # Try finding any file with device name
                    matches = list(options.baseline.glob(f"*{device}*"))
                    if matches:
                        cand = matches[0]
                base_file = cand
            else:
                base_file = options.baseline

            if not base_file.exists():
                return [
                    DiffItemResult(
                        device=device,
                        subject="config",
                        outcome=None,
                        error=f"Baseline file not found: {base_file}",
                    )
                ]

            base_text = _read_text(base_file)
            with _get_session(device, options.config, options.session_pool) as s:
                curr_text = s.execute_command("/export compact")

            _save_artifact(device, "export_compact", curr_text, options.save_current)

            outcome = _diff_texts(
                baseline_text=base_text,
                current_text=curr_text,
                baseline_label=str(base_file),
                current_label=f"{device}:/export compact",
                ignore_patterns=options.ignore_patterns or [],
                heuristic=options.heuristic,
            )
            results.append(
                DiffItemResult(device=device, subject="config", outcome=outcome)
            )

        elif is_command:
            # Diff command vs file
            cmd_base_file: Path | None
            if options.baseline.is_dir():
                cmd_base_file = _find_baseline_file_for_command(options.baseline, subj)
            else:
                cmd_base_file = options.baseline

            if not cmd_base_file or not cmd_base_file.exists():
                return [
                    DiffItemResult(
                        device=device,
                        subject=subj,
                        outcome=None,
                        error=f"Baseline file not found for command: {subj}",
                    )
                ]

            base_text = _read_text(cmd_base_file)
            with _get_session(device, options.config, options.session_pool) as s:
                curr_text = s.execute_command(subj)

            _save_artifact(device, subj, curr_text, options.save_current)

            outcome = _diff_texts(
                baseline_text=base_text,
                current_text=curr_text,
                baseline_label=str(cmd_base_file),
                current_label=f"{device}:{subj}",
                ignore_patterns=options.ignore_patterns or [],
                heuristic=options.heuristic,
            )
            results.append(DiffItemResult(device=device, subject=subj, outcome=outcome))

        else:
            # Sequence diff
            if not options.baseline.is_dir():
                msg = "For sequence diff, baseline must be a directory."
                raise NetworkToolkitError(msg)

            seq_cmds = sequence_manager.resolve(device, subj)
            if not seq_cmds:
                return [
                    DiffItemResult(
                        device=device,
                        subject=subj,
                        outcome=None,
                        error=f"Sequence '{subj}' empty or not found for {device}",
                    )
                ]

            with _get_session(device, options.config, options.session_pool) as s:
                for cmd in seq_cmds:
                    seq_base_file: Path | None = _find_baseline_file_for_command(
                        options.baseline, cmd
                    )
                    if not seq_base_file:
                        results.append(
                            DiffItemResult(
                                device=device,
                                subject=cmd,
                                outcome=None,
                                error="Baseline file missing",
                            )
                        )
                        continue

                    base_text = _read_text(seq_base_file)
                    curr_text = s.execute_command(cmd)
                    _save_artifact(device, cmd, curr_text, options.save_current)

                    outcome = _diff_texts(
                        baseline_text=base_text,
                        current_text=curr_text,
                        baseline_label=str(seq_base_file),
                        current_label=f"{device}:{cmd}",
                        ignore_patterns=options.ignore_patterns or [],
                        heuristic=options.heuristic,
                    )
                    results.append(
                        DiffItemResult(device=device, subject=cmd, outcome=outcome)
                    )

    except Exception as e:
        return [DiffItemResult(device=device, subject=subj, outcome=None, error=str(e))]

    return results


def diff_files(
    file_a: Path,
    file_b: Path,
    *,
    heuristic: bool = False,
    ignore_patterns: list[str] | None = None,
) -> DiffOutcome:
    """Compare two local files."""
    text_a = _read_text(file_a)
    text_b = _read_text(file_b)

    return _diff_texts(
        baseline_text=text_a,
        current_text=text_b,
        baseline_label=str(file_a),
        current_label=str(file_b),
        ignore_patterns=ignore_patterns or [],
        heuristic=heuristic,
    )


def diff_targets(options: DiffOptions) -> DiffResult:
    """Execute the diff operation based on the provided options."""
    subj = options.subject.strip()
    is_config = subj.lower() == "config"
    is_command = subj.startswith("/")

    sm = SequenceManager(options.config)
    mode_label = "config" if is_config else ("command" if is_command else "sequence")
    cmd_ctx = f"diff_{options.targets}_{mode_label}_{_sanitize_filename(subj)}"

    # Initialize ResultsManager if needed
    _ = ResultsManager(
        options.config,
        store_results=options.store_results,
        results_dir=options.results_dir,
        command_context=cmd_ctx,
    )

    target_resolution = resolve_named_targets(options.config, options.targets)
    devices = target_resolution.resolved_devices
    unknown = target_resolution.unknown_targets
    if unknown and not devices:
        msg = f"Target(s) not found: {', '.join(unknown)}"
        raise NetworkToolkitError(msg)

    results: list[DiffItemResult] = []
    total_changed = 0
    total_missing = 0

    # Device-to-device mode: exactly two devices and no baseline
    if options.baseline is None and len(devices) == 2:
        dev_a, dev_b = devices[0], devices[1]

        try:

            def _fetch_device_output(dev: str) -> str:
                with _get_session(dev, options.config, options.session_pool) as s:
                    if is_config:
                        return s.execute_command("/export compact")
                    elif is_command:
                        return s.execute_command(subj)
                    else:
                        msg = "Device-to-device diff only supports 'config' or a single command."
                        raise NetworkToolkitError(msg)

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_a = executor.submit(_fetch_device_output, dev_a)
                future_b = executor.submit(_fetch_device_output, dev_b)
                curr_a = future_a.result()
                curr_b = future_b.result()

            _save_artifact(
                dev_a,
                "export_compact" if is_config else subj,
                curr_a,
                options.save_current,
            )
            _save_artifact(
                dev_b,
                "export_compact" if is_config else subj,
                curr_b,
                options.save_current,
            )

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

    # Parallel execution
    parallel_results = execute_parallel(
        devices,
        partial(_perform_device_diff, options=options, sequence_manager=sm),
    )

    # Flatten results
    flat_results: list[DiffItemResult] = []
    for res_list in parallel_results:
        flat_results.extend(res_list)

    # Sort by device name
    flat_results.sort(key=lambda x: x.device)

    # Calculate totals
    for res in flat_results:
        if res.error and "Baseline file missing" in res.error:
            total_missing += 1
        elif res.outcome and res.outcome.changed:
            total_changed += 1
        elif res.error and "Baseline file not found" in res.error:
            # This covers the case where the whole device failed due to missing baseline
            total_missing += 1

    return DiffResult(
        results=flat_results,
        total_changed=total_changed,
        total_missing=total_missing,
        device_pair_diff=False,
    )
