"""`nw diff` command implementation.

Provides smart diffing of device configuration and operational state:
 - Config diff: compares current RouterOS export (compact) with a baseline file
 - Command diff: compares a single command output with a baseline file
 - Sequence diff: compares a sequence's per-command outputs with files in a baseline directory

Subject-based UX:
    nw diff <targets> <subject>
Where subject is one of:
    - "config" (special keyword for /export compact)
    - "/..." (a RouterOS command)
    - a sequence name (resolved per-device)

Device-to-device: if exactly two devices are provided and no --baseline is supplied,
the command compares outputs directly between the devices.

Exit codes:
 - 0: No differences
 - 1: Differences found or baseline missing/mismatched
 - 2: Usage / configuration error (bad inputs)
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.output import OutputMode
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.results_enhanced import ResultsManager
from network_toolkit.sequence_manager import SequenceManager


@dataclass
class DiffOutcome:
    changed: bool
    output: str


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


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Remote Operations",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    def diff(
        target: Annotated[
            str,
            typer.Argument(
                help=(
                    "Device/group name or comma-separated list (e.g. 'sw-1,lab_devices')"
                ),
            ),
        ],
        subject: Annotated[
            str,
            typer.Argument(
                help=(
                    "Subject to diff: 'config' for /export compact, a RouterOS command "
                    "starting with '/', or the name of a configured sequence."
                ),
            ),
        ],
        *,
        baseline: Annotated[
            Path | None,
            typer.Option(
                "--baseline",
                "-b",
                help=(
                    "Baseline file (for config/command) or directory (for sequence)."
                ),
            ),
        ] = None,
        ignore: Annotated[
            list[str] | None,
            typer.Option(
                "--ignore",
                help=("Regex to ignore lines; repeat for multiple patterns."),
            ),
        ] = None,
        save_current: Annotated[
            Path | None,
            typer.Option(
                "--save-current",
                help=(
                    "Optional path to save the current fetched state "
                    "(file or directory)."
                ),
            ),
        ] = None,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
        store_results: Annotated[
            bool,
            typer.Option(
                "--store-results",
                "-s",
                help="Store diff outputs to files",
            ),
        ] = False,
        results_dir: Annotated[
            str | None,
            typer.Option("--results-dir", help="Override results directory"),
        ] = None,
    ) -> None:
        """Diff config, a command, or a sequence.

        Examples:
          - nw diff sw-acc1 config -b baseline/export_compact.txt
          - nw diff sw-acc1 "/system/resource/print" -b baseline/resource.txt
          - nw diff lab_devices system_info -b baseline_dir/
          - nw diff sw-acc1,sw-acc2 "/system/resource/print"   # device-to-device
          - nw diff sw-acc1,sw-acc2 config                      # device-to-device
        """
        # Create command context with proper styling
        ctx = CommandContext(
            output_mode=output_mode,
            verbose=verbose,
            config_file=config_file,
        )

        subj = subject.strip()
        is_config = subj.lower() == "config"
        is_command = subj.startswith("/")

        try:
            config = load_config(config_file)
        except Exception as e:  # pragma: no cover - load errors covered elsewhere
            ctx.print_error(f"Failed to load config: {e}")
            raise typer.Exit(2) from None

        sm = SequenceManager(config)
        mode_label = (
            "config" if is_config else ("command" if is_command else "sequence")
        )
        cmd_ctx = f"diff_{target}_{mode_label}_{_sanitize_filename(subj)}"
        results_mgr = ResultsManager(
            config,
            store_results=store_results,
            results_dir=results_dir,
            command_context=cmd_ctx,
        )

        # Resolve device list (comma-separated targets supported)
        def resolve_targets(target_expr: str) -> tuple[list[str], list[str]]:
            requested = [t.strip() for t in target_expr.split(",") if t.strip()]
            devices: list[str] = []
            unknowns: list[str] = []

            def _add(name: str) -> None:
                if name not in devices:
                    devices.append(name)

            for name in requested:
                if config.devices and name in config.devices:
                    _add(name)
                elif config.device_groups and name in config.device_groups:
                    for m in config.get_group_members(name):
                        _add(m)
                else:
                    unknowns.append(name)
            return devices, unknowns

        devices, unknown = resolve_targets(target)
        if unknown and not devices:
            ctx.print_error("Error: target(s) not found: " + ", ".join(unknown))
            raise typer.Exit(2)
        if unknown:
            ctx.print_warning("Ignoring unknown target(s): " + ", ".join(unknown))

        # Late import to preserve test patches of network_toolkit.cli.DeviceSession
        from network_toolkit.cli import DeviceSession

        total_changed = 0
        total_missing = 0
        per_device_reports: list[
            tuple[str, list[tuple[str, DiffOutcome | None, str]]]
        ] = []

        # Helper to optionally save current fetches
        def _save_current_artifact(dev: str, name: str, text: str) -> None:
            if not save_current:
                return
            path = Path(save_current)
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

        try:
            # Device-to-device mode: exactly two devices and no baseline
            device_pair = 2
            if baseline is None and len(devices) == device_pair:
                dev_a, dev_b = devices[0], devices[1]
                label_pair = f"{dev_a} vs {dev_b}"
                rows: list[tuple[str, DiffOutcome | None, str]] = []

                if is_config:
                    with DeviceSession(dev_a, config) as sa:
                        curr_a = sa.execute_command("/export compact")
                    with DeviceSession(dev_b, config) as sb:
                        curr_b = sb.execute_command("/export compact")
                    _save_current_artifact(dev_a, "export_compact", curr_a)
                    _save_current_artifact(dev_b, "export_compact", curr_b)
                    outcome = _diff_texts(
                        baseline_text=curr_a,
                        current_text=curr_b,
                        baseline_label=f"{dev_a}:/export compact",
                        current_label=f"{dev_b}:/export compact",
                        ignore_patterns=ignore or [],
                    )
                    rows.append(("config", outcome, ""))

                elif is_command:
                    with DeviceSession(dev_a, config) as sa:
                        curr_a = sa.execute_command(subj)
                    with DeviceSession(dev_b, config) as sb:
                        curr_b = sb.execute_command(subj)
                    _save_current_artifact(dev_a, subj, curr_a)
                    _save_current_artifact(dev_b, subj, curr_b)
                    outcome = _diff_texts(
                        baseline_text=curr_a,
                        current_text=curr_b,
                        baseline_label=f"{dev_a}:{subj}",
                        current_label=f"{dev_b}:{subj}",
                        ignore_patterns=ignore or [],
                    )
                    rows.append((subj, outcome, ""))

                else:  # sequence
                    cmds_a: list[str] | None = sm.resolve(subj, dev_a)
                    cmds_b: list[str] | None = sm.resolve(subj, dev_b)
                    if not cmds_a and not cmds_b:
                        rows.append(
                            (
                                subj,
                                None,
                                f"Sequence '{subj}' not found for {label_pair}",
                            )
                        )
                    else:
                        base_list = cmds_a or cmds_b or []
                        with (
                            DeviceSession(dev_a, config) as sa,
                            DeviceSession(dev_b, config) as sb,
                        ):
                            for cmd in base_list:
                                curr_a = sa.execute_command(cmd)
                                curr_b = sb.execute_command(cmd)
                                _save_current_artifact(dev_a, cmd, curr_a)
                                _save_current_artifact(dev_b, cmd, curr_b)
                                outcome = _diff_texts(
                                    baseline_text=curr_a,
                                    current_text=curr_b,
                                    baseline_label=f"{dev_a}:{cmd}",
                                    current_label=f"{dev_b}:{cmd}",
                                    ignore_patterns=ignore or [],
                                )
                                rows.append((cmd, outcome, ""))

                per_device_reports.append((label_pair, rows))
                total_changed = sum(int(r[1].changed) for r in rows if r[1] is not None)
                total_missing = sum(1 for r in rows if r[1] is None)

            elif is_config:
                if baseline is None:
                    ctx.print_error(
                        "--baseline FILE is required for 'config' diffs when "
                        "not comparing two devices."
                    )
                    raise typer.Exit(2)

                for dev in devices:
                    with DeviceSession(dev, config) as session:
                        current = session.execute_command("/export compact")
                    _save_current_artifact(dev, "export_compact", current)
                    base_text = _read_text(baseline)
                    outcome = _diff_texts(
                        baseline_text=base_text,
                        current_text=current,
                        baseline_label=str(baseline),
                        current_label=f"{dev}:/export compact",
                        ignore_patterns=ignore or [],
                    )
                    per_device_reports.append((dev, [("config", outcome, "")]))
                    total_changed += int(outcome.changed)

            elif is_command:
                if baseline is None:
                    ctx.print_error(
                        "--baseline FILE is required for single-device command "
                        "diffs. Use two devices (comma-separated) to diff "
                        "device-to-device."
                    )
                    raise typer.Exit(2)
                for dev in devices:
                    with DeviceSession(dev, config) as session:
                        current = session.execute_command(subj)
                    _save_current_artifact(dev, subj, current)
                    base_text = _read_text(baseline)
                    outcome = _diff_texts(
                        baseline_text=base_text,
                        current_text=current,
                        baseline_label=str(baseline),
                        current_label=f"{dev}:{subj}",
                        ignore_patterns=ignore or [],
                    )
                    per_device_reports.append((dev, [(subj, outcome, "")]))
                    total_changed += int(outcome.changed)

            else:  # sequence
                if baseline is None:
                    ctx.print_error(
                        "--baseline DIR is required for single-device sequence "
                        "diffs. Use two devices (comma-separated) to diff "
                        "device-to-device."
                    )
                    raise typer.Exit(2)
                if not baseline.exists() or not baseline.is_dir():
                    ctx.print_error("Baseline must be an existing directory.")
                    raise typer.Exit(2)

                for dev in devices:
                    commands: list[str] | None = sm.resolve(subj, dev)
                    if not commands:
                        per_device_reports.append(
                            (
                                dev,
                                [
                                    (
                                        subj,
                                        None,
                                        f"Sequence '{subj}' not found for device",
                                    )
                                ],
                            )
                        )
                        total_missing += 1
                        continue

                    report_rows: list[tuple[str, DiffOutcome | None, str]] = []
                    with DeviceSession(dev, config) as session:
                        for cmd in commands:
                            current = session.execute_command(cmd)
                            _save_current_artifact(dev, cmd, current)
                            base_file = _find_baseline_file_for_command(baseline, cmd)
                            if not base_file:
                                note = (
                                    f"No baseline file found for command: {cmd} "
                                    f"(expected like 'cmd_"
                                    f"{_sanitize_filename(cmd)}.txt')"
                                )
                                report_rows.append((cmd, None, note))
                                total_missing += 1
                                continue

                            base_text = _read_text(base_file)
                            outcome = _diff_texts(
                                baseline_text=base_text,
                                current_text=current,
                                baseline_label=str(base_file),
                                current_label=f"{dev}:{cmd}",
                                ignore_patterns=ignore or [],
                            )
                            report_rows.append((cmd, outcome, ""))
                            total_changed += int(outcome.changed)

                    per_device_reports.append((dev, report_rows))

            # Render report and optionally store
            any_diffs = total_changed > 0 or total_missing > 0

            for dev, rows in per_device_reports:
                ctx.print_info(f"Device: {dev}")
                for name, res, note in rows:
                    if res is None:
                        ctx.print_warning(f"{name}: {note}")
                    elif not res.changed:
                        ctx.print_info(f"{name}: identical")
                    else:
                        ctx.print_info(f"{name}: differences found")
                        if res.output:
                            ctx.output.print_output(res.output)

                        if results_mgr.store_results and results_mgr.session_dir:
                            # Store diff output as a command result for visibility
                            results_mgr.store_command_result(
                                dev, f"DIFF {name}", res.output or "(no diff)"
                            )

                ctx.output.print_separator()

            if any_diffs:
                ctx.print_info(
                    f"Summary: diffs={total_changed}, missing_baseline={total_missing}"
                )
                raise typer.Exit(1)
            else:
                ctx.print_success("No differences detected.")
                raise typer.Exit(0)

        except NetworkToolkitError as e:  # pragma: no cover - error path
            ctx.print_error(str(e))
            raise typer.Exit(1) from None
