"""A RouterOS reboot and the saved evidence that proves its recovery."""

from __future__ import annotations

import json
import signal
import socket
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from network_toolkit import intent, lab
from network_toolkit.inventory.resolve import resolve_named_targets
from network_toolkit.platforms.mikrotik_routeros import intent as routeros
from network_toolkit.traffic import NS

if TYPE_CHECKING:
    from network_toolkit.client import NetworkaClient

# RouterOS accepted password logins spaced five seconds apart on the Small lab.
POLL_S = 5


def validate_target(client: NetworkaClient, topology: lab.Lab, switch: str) -> None:
    node = topology.node(switch)
    targets = resolve_named_targets(client.config, switch)
    if (
        targets.resolved_devices != [switch]
        or targets.unknown_targets
        or switch in client.groups
        or switch not in client.devices
    ):
        msg = f"Reboot target {switch!r} must identify one lab device."
        raise lab.LabError(msg)
    device = client.devices[switch]
    networks = json.loads(
        lab.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{json .NetworkSettings.Networks}}",
                node.container,
            ]
        )
    )
    live_addresses = {endpoint.get("IPAddress") for endpoint in networks.values()}
    if (
        node.kind != "mikrotik_chr"
        or device.device_type != "mikrotik_routeros"
        or device.host != node.address
        or node.address not in live_addresses
    ):
        msg = f"Reboot target {switch!r} must be the RouterOS switch at its topology management address."
        raise lab.LabError(msg)


class _Deadline(BaseException):
    """Escape even an in-progress transport call that catches ordinary exceptions."""


@contextmanager
def _deadline(seconds: float) -> Iterator[None]:
    # Local live runs execute on the Linux lab host. A blocked SSH read must also
    # respect the recovery deadline, including during a full set of state checks.
    def expired(_number: int, _frame: object) -> None:
        raise _Deadline

    previous = signal.signal(signal.SIGALRM, expired)
    timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    start = time.monotonic()
    try:
        yield
    except _Deadline:
        msg = f"Switch recovery exceeded {seconds:g} s."
        raise lab.LabError(msg) from None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if timer[0]:
            signal.setitimer(
                signal.ITIMER_REAL,
                max(0.000001, timer[0] - (time.monotonic() - start)),
                timer[1],
            )


def _ssh_ready(host: str, port: int) -> bool:
    # Read the SSH greeting without a login while the switch is booting.
    try:
        with socket.create_connection((host, port), timeout=POLL_S) as connection:
            with connection.makefile("rb") as stream:
                return stream.readline(256).startswith(b"SSH-")
    except OSError:
        return False


def _restarted(before: int, after: int, elapsed_ns: int) -> bool:
    return 0 <= after < before and after <= elapsed_ns


def run(
    client: NetworkaClient,
    session: lab.Session,
    switch: str,
    number: int,
    wait_s: float,
    items: list[intent.IntentItem],
    options: Mapping[str, Any],
) -> None:
    validate_target(client, session.lab, switch)
    before = routeros.collect_uptime(client, switch, **options)
    before_ns = routeros.uptime_ns(before)
    if before_ns <= 0:
        msg = f"Cannot prove a lower uptime after reboot of {switch}."
        raise lab.LabError(msg)
    dispatch = session.mark("reboot_start", switch=switch, number=number, uptime=before)
    port = client.devices[switch].port or client.config.general.port
    with _deadline(wait_s):
        command = routeros.reboot(client, switch, **options)
        session.mark("reboot_command", switch=switch, number=number, reply=command)
        proven = False
        attempt = 0
        while True:
            time.sleep(POLL_S)
            if not proven:
                if not _ssh_ready(session.lab.node(switch).address, port):
                    continue
                reading = routeros.collect_uptime(client, switch, **options)
                observed = session.mark(
                    "reboot_uptime", switch=switch, number=number, uptime=reading
                )
                try:
                    after_ns = routeros.uptime_ns(reading)
                except ValueError:
                    continue
                proven = _restarted(
                    before_ns, after_ns, observed["mono_ns"] - dispatch["mono_ns"]
                )
                if not proven:
                    continue
            attempt += 1
            directory = session.directory / "recovery" / str(number) / str(attempt)
            health = intent.run_intent(client, items, directory, **options)
            session.mark(
                "reboot_health",
                switch=switch,
                number=number,
                attempt=attempt,
                verdict=health.verdict,
            )
            if health.verdict == "pass":
                return


def proof(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    switch: str,
    number: int,
    wait_s: float,
    items: list[intent.IntentItem],
) -> dict[str, Any]:
    """Recheck the raw switch readings and complete lab state against the deadline."""
    result: dict[str, Any] = {"switch": switch, "verdict": "error", "limit_s": wait_s}
    own = [e for e in events if e.get("number") == number and e.get("switch") == switch]
    try:
        [start] = [e for e in own if e["name"] == "reboot_start"]
        [command] = [e for e in own if e["name"] == "reboot_command"]
        if command["reply"]["command"] != routeros.REBOOT:
            msg = "The recorded command is not the fixed RouterOS reboot."
            raise ValueError(msg)
        before = routeros.uptime_ns(start["uptime"])
        result["before_uptime_s"] = before / NS
        for probe in (e for e in own if e["name"] == "reboot_uptime"):
            try:
                after = routeros.uptime_ns(probe["uptime"])
            except ValueError:
                continue
            elapsed = probe["mono_ns"] - start["mono_ns"]
            if _restarted(before, after, elapsed):
                result.update(after_uptime_s=after / NS, elapsed_s=elapsed / NS)
                break
        else:
            msg = "The recorded uptime does not prove a new boot."
            raise ValueError(msg)
        health = [e for e in own if e["name"] == "reboot_health"][-1]
        attempt = int(health["attempt"])
        path = folder / "recovery" / str(number) / str(attempt) / intent.EVIDENCE_FILE
        recovered = intent.replay_intent(items, intent.load_json(path.read_text()))
        elapsed = (health["mono_ns"] - start["mono_ns"]) / NS
        result.update(healthy_s=elapsed, state=recovered.verdict)
        if not result["elapsed_s"] <= elapsed <= wait_s or recovered.verdict != "pass":
            msg = "The full lab state did not recover within the deadline."
            raise ValueError(msg)
        if command["reply"].get("error"):
            msg = f"RouterOS did not confirm the reboot command: {command['reply']['error']}"
            raise ValueError(msg)
    except (OSError, KeyError, IndexError, ValueError, intent.IntentError) as error:
        result["reason"] = str(error)
        return result
    result["verdict"] = "pass"
    return result
