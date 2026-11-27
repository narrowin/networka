# SPDX-License-Identifier: MIT
"""Sample RouterOS bridge host entries alongside timed lab steps."""

from __future__ import annotations

import itertools
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any

from network_toolkit import intent, lab, traffic
from network_toolkit.platforms.mikrotik_routeros import intent as routeros

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from network_toolkit.client import NetworkaClient

WATCH_DIR = "host-entries"


@dataclass(frozen=True)
class Spec:
    interval_s: float
    bridge: str
    devices: tuple[str, ...]
    macs: tuple[str, ...]


def parse(raw: Any, where: str) -> Spec:
    """Read the interval, bridge, devices and MACs, once for live and replay."""
    if not isinstance(raw, dict) or set(raw) != {
        "interval_s",
        "bridge",
        "devices",
        "macs",
    }:
        msg = f"{where}: requires interval_s, bridge, devices and macs"
        raise lab.LabError(msg)
    period = raw["interval_s"]
    if (
        isinstance(period, bool)
        or not isinstance(period, (float, int))
        or not math.isfinite(period)
        or period <= 0
    ):
        msg = f"{where}: interval_s must be a positive number"
        raise lab.LabError(msg)
    try:
        bridge = intent.name(raw["bridge"], "bridge")
        if not isinstance(raw["devices"], list) or not isinstance(raw["macs"], list):
            msg = "devices and macs must be lists"
            raise ValueError(msg)
        devices = tuple(intent.name(n, "device") for n in raw["devices"])
        macs = tuple(intent.mac(m).lower() for m in raw["macs"])
        if (
            not devices
            or len(set(devices)) != len(devices)
            or any("/" in n for n in devices)
        ):
            msg = "devices must be non-empty, unique lab node names"
            raise ValueError(msg)
        if not macs or len(set(macs)) != len(macs):
            msg = "macs must be a non-empty list of distinct addresses"
            raise ValueError(msg)
    except ValueError as error:
        msg = f"{where}: {error}"
        raise lab.LabError(msg) from None
    return Spec(float(period), bridge, devices, macs)


def _commands(spec: Spec) -> tuple[str, ...]:
    return (
        routeros.bridge_print(spec.bridge),
        *(routeros.host_print(mac) for mac in spec.macs),
    )


def _sample(
    client: NetworkaClient,
    device: str,
    commands: tuple[str, ...],
    period: float,
    path: Path,
    stop: Event,
    options: Mapping[str, Any],
) -> int:
    """Run all reads for one peer in one pooled request per sample."""
    samples = 0
    with path.open("w", encoding="utf-8", buffering=1) as target:
        while not stop.is_set():
            tick = time.monotonic()
            started = time.time_ns()
            raw = routeros.read_replies(client, device, *commands, **options)
            sample = {"started_ns": started, "done_ns": time.time_ns(), "raw": raw}
            target.write(json.dumps(sample) + "\n")
            samples += 1
            stop.wait(max(0, period - (time.monotonic() - tick)))
    return samples


@contextmanager
def sample_entries(
    client: NetworkaClient,
    session: lab.Session,
    spec: Spec | None,
    options: Mapping[str, Any],
) -> Iterator[None]:
    """Watch without adding communication time to any cable hold."""
    if spec is None:
        yield
        return
    for node in spec.devices:
        session.lab.node(node)
        device = client.devices.get(node)
        if device is None or device.device_type != "mikrotik_routeros":
            msg = f"host-entry watch needs RouterOS device {node} in the lab inventory"
            raise lab.LabError(msg)
    directory = session.directory / WATCH_DIR
    directory.mkdir()
    commands = _commands(spec)
    stop = Event()
    session.mark("host_watch_started", devices=spec.devices, interval_s=spec.interval_s)
    with ThreadPoolExecutor(max_workers=len(spec.devices)) as workers:
        futures = {
            device: workers.submit(
                _sample,
                client,
                device,
                commands,
                spec.interval_s,
                directory / f"{device}.jsonl",
                stop,
                options,
            )
            for device in spec.devices
        }
        original: BaseException | None = None
        try:
            yield
        except BaseException as error:
            original = error
            raise
        finally:
            stop.set()
            try:
                counts = {device: future.result() for device, future in futures.items()}
                session.mark("host_watch_stopped", samples=counts)
            except Exception as error:
                session.record_restore_errors(
                    [f"host-entry watch shutdown: {error}"], original
                )


def proof(
    folder: Path, events: Sequence[Mapping[str, Any]], spec: Spec
) -> dict[str, Any]:
    """Require a decisive sample on both peers in each step and each target MAC to remain present."""
    problems: list[str] = []
    details: dict[str, Any] = {}
    result = {"verdict": "error", "interval_s": spec.interval_s, "devices": details}
    try:
        [started] = [event for event in events if event["name"] == "host_watch_started"]
        [stopped] = [event for event in events if event["name"] == "host_watch_stopped"]
        [end] = [event["epoch_ns"] for event in events if event["name"] == "steps_end"]
        starts = [
            (event["step"], event["epoch_ns"])
            for event in events
            if event["name"] == "step_start"
        ]
        if (
            not starts
            or tuple(started["devices"]) != spec.devices
            or started["interval_s"] != spec.interval_s
        ):
            msg = "The saved host watch does not match the configured watch"
            raise ValueError(msg)
        first = starts[0][1]
        if not started["epoch_ns"] <= first < stopped["epoch_ns"] <= end:
            msg = "The saved host watch did not cover the step sequence"
            raise ValueError(msg)
        for device in spec.devices:
            raw = folder / WATCH_DIR / f"{device}.jsonl"
            rows = [
                intent.load_json(line)
                for line in raw.read_text(encoding="utf-8").splitlines()
            ]
            stamps = [row["started_ns"] for row in rows]
            if len(rows) != stopped["samples"][device] or stamps != sorted(set(stamps)):
                msg = f"{device}: saved host samples are missing or out of order"
                raise ValueError(msg)
            counts: dict[str, int] = {}
            missing: dict[str, list[float]] = {mac: [] for mac in spec.macs}
            for n, (name, lower) in enumerate(starts):
                upper = starts[n + 1][1] if n + 1 < len(starts) else end
                # Cable command and confirmation time are outside the hold.
                applied = next(
                    (
                        event["epoch_ns"]
                        for event in events
                        if event["name"] == "cable_observed"
                        and lower <= event["epoch_ns"] < upper
                    ),
                    lower,
                )
                samples = [
                    row
                    for row in rows
                    if applied <= row["started_ns"] <= row["done_ns"] < upper
                ]
                if not samples:
                    msg = f"{device}: no host-table sample in {name}"
                    raise ValueError(msg)
                counts[name] = len(samples)
                for row in samples:
                    if not row["started_ns"] <= row["done_ns"] <= stopped["epoch_ns"]:
                        msg = f"{device}: host sample timestamps are inconsistent"
                        raise ValueError(msg)
                    for mac in spec.macs:
                        if routeros.host_entry(row["raw"], spec.bridge, mac) is None:
                            missing[mac].append(
                                traffic.seconds(row["started_ns"] - first)
                            )
            details[device] = {
                "samples_per_step": counts,
                "missing_samples_s": missing,
                "max_sample_interval_s": max(
                    (traffic.seconds(b - a) for a, b in itertools.pairwise(stamps)),
                    default=0,
                ),
            }
            problems.extend(
                f"{device} lost {mac} from its bridge host table"
                for mac, times in missing.items()
                if times
            )
    except (OSError, KeyError, TypeError, ValueError) as error:
        return {**result, "reason": str(error)}
    if problems:
        return {**result, "verdict": "fail", "reason": ". ".join(problems)}
    return {**result, "verdict": "pass"}
