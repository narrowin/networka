"""DeepDiff comparison of native JSON in saved nw run results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepdiff import DeepDiff

from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.intent import load_json


@dataclass(frozen=True)
class StructuredDifference:
    """Differences for one device and exact command, without collection metadata."""

    device: str
    command: str
    changes: dict[str, Any]
    comparison: DeepDiff


def _error(path: Path, reason: str) -> NetworkToolkitError:
    return NetworkToolkitError(f"{path}: {reason}")


def _read(path: Path) -> Any:
    try:
        return load_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise _error(path, f"cannot read JSON: {error}") from None


def _load(path: Path) -> dict[tuple[str, str], Any]:
    """Index saved replies by device/command and validate collection summaries."""
    directory = path.is_dir()
    files = sorted(p for p in path.rglob("*") if p.is_file()) if directory else [path]
    replies: dict[tuple[str, str], Any] = {}
    summaries: list[tuple[Path, dict[str, Any]]] = []
    for file in files:
        if directory and file.suffix != ".json":
            raise _error(
                file, "structured results require general.results_format: json"
            )
        data = _read(file)
        envelope = isinstance(data, dict) and {"nw_command", "timestamp"} <= data.keys()
        if isinstance(data, dict) and (directory or envelope):
            if data.get("error") is not None or data.get("status") == "failed":
                raise _error(
                    file, f"saved collection error: {data.get('error', 'failed')}"
                )
            if "results_summary" in data or "failed_device_list" in data:
                summaries.append((file, data))
                continue
        if not envelope:
            if directory:
                raise _error(file, "expected a saved nw run result")
            return {("JSON", "payload"): data}
        device, command, output = (
            data.get("device_name"),
            data.get("command"),
            data.get("output"),
        )
        if (
            not isinstance(device, str)
            or not device
            or not isinstance(command, str)
            or not command
        ):
            raise _error(file, "saved result needs a device name and command")
        if not isinstance(output, str):
            raise _error(file, "saved result has no command output")
        try:
            payload = load_json(output)
        except ValueError as error:
            raise _error(file, f"command did not return native JSON: {error}") from None
        identity = (device, command)
        if identity in replies:
            raise _error(file, f"duplicate saved result for {device} / {command}")
        replies[identity] = payload
    if not replies:
        raise _error(path, "no saved command replies to compare")
    for file, summary in summaries:
        if "results_summary" in summary:
            commands = summary["results_summary"]
            device = summary.get("device_name")
            if (
                not isinstance(commands, dict)
                or not commands
                or not isinstance(device, str)
            ):
                raise _error(file, "invalid sequence summary")
            actual = {command for name, command in replies if name == device}
            if set(commands) != actual or summary.get("commands_executed") != len(
                commands
            ):
                raise _error(
                    file, "sequence summary does not match saved command replies"
                )
        else:
            devices = summary.get("succeeded_device_list")
            if summary["failed_device_list"] or summary.get("failed_devices") != 0:
                raise _error(file, "the saved group collection contains failed devices")
            if not isinstance(devices, list) or not all(
                isinstance(d, str) for d in devices
            ):
                raise _error(file, "invalid group summary")
            actual_devices = {device for device, _ in replies}
            if (
                set(devices) != actual_devices
                or len(devices) != len(set(devices))
                or summary.get("total_devices") != len(devices)
                or summary.get("succeeded_devices") != len(devices)
            ):
                raise _error(file, "group summary does not match saved device replies")
    return replies


def _keyed(payload: Any, key: str, label: str) -> dict[str | int, Any]:
    if not isinstance(payload, list):
        msg = f"{label}: --key requires a JSON array of objects"
        raise NetworkToolkitError(msg)
    indexed: dict[str | int, Any] = {}
    for row in payload:
        if (
            not isinstance(row, dict)
            or key not in row
            or type(row[key]) not in (str, int)
        ):
            msg = f"{label}: each row needs a string or integer identity field {key!r}"
            raise NetworkToolkitError(msg)
        identity = row[key]
        if identity in indexed:
            msg = f"{label}: duplicate {key} identity {identity!r}"
            raise NetworkToolkitError(msg)
        indexed[identity] = row
    return indexed


def compare_saved_json(
    first: Path,
    second: Path,
    *,
    key: str | None = None,
    exclude_paths: list[str] | None = None,
) -> list[StructuredDifference]:
    """Compare full native payloads, preserving order unless a table key is supplied.

    Accepts saved JSON result files, run directories, or two native JSON files.
    Both saved collections must cover the same device/command identities.
    Exclusions apply to payload paths after optional top-level table indexing.
    """
    left, right = _load(first), _load(second)
    if left.keys() != right.keys():
        missing = sorted(left.keys() - right.keys())
        added = sorted(right.keys() - left.keys())
        msg = f"saved collection scopes differ; missing device/commands: {missing}; added: {added}"
        raise NetworkToolkitError(msg)
    results = []
    for device, command in sorted(left):
        a, b = left[(device, command)], right[(device, command)]
        if key is not None:
            a = _keyed(a, key, f"{first} / {device} / {command}")
            b = _keyed(b, key, f"{second} / {device} / {command}")
        difference = DeepDiff(
            a,
            b,
            exclude_paths=exclude_paths,
            ignore_order=False,
            ignore_private_variables=False,
            verbose_level=2,
            threshold_to_diff_deeper=0,
        )
        stats = difference.get_stats()
        if stats.get("MAX PASS LIMIT REACHED") or stats.get("MAX DIFF LIMIT REACHED"):
            msg = f"comparison did not complete for {device} / {command}"
            raise NetworkToolkitError(msg)
        changes = json.loads(difference.to_json(force_use_builtin_json=True))
        results.append(StructuredDifference(device, command, changes, difference))
    return results
