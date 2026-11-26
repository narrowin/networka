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


def validate_target(
    client: NetworkaClient, topology: lab.Lab, switch: str, operation: str = "Reboot"
) -> None:
    node = topology.node(switch)
    targets = resolve_named_targets(client.config, switch)
    if (
        targets.resolved_devices != [switch]
        or targets.unknown_targets
        or switch in client.groups
        or switch not in client.devices
    ):
        msg = f"{operation} target {switch!r} must identify one lab device."
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
        msg = f"{operation} target {switch!r} must be the RouterOS switch at its topology management address."
        raise lab.LabError(msg)


class _Deadline(BaseException):
    """Escape even an in-progress transport call that catches ordinary exceptions."""


@contextmanager
def _deadline(
    seconds: float, operation: str = "Switch recovery", since_ns: int | None = None
) -> Iterator[None]:
    # Local live runs execute on the Linux lab host. A blocked SSH read must also
    # respect the recovery deadline, including during a full set of state checks.
    # since_ns starts the deadline at the dispatch mark that the proof measures from.
    def expired(_number: int, _frame: object) -> None:
        raise _Deadline

    left = seconds
    if since_ns is not None:
        left -= (time.monotonic_ns() - since_ns) / NS
    previous = signal.signal(signal.SIGALRM, expired)
    # A zero timer would disable the alarm instead of expiring at once.
    timer = signal.setitimer(signal.ITIMER_REAL, max(0.000001, left))
    start = time.monotonic()
    try:
        yield
    except _Deadline:
        msg = f"{operation} exceeded {seconds:g} s."
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
    with _deadline(wait_s, since_ns=dispatch["mono_ns"]):
        command = routeros.reboot(client, switch, **options)
        session.mark("reboot_command", switch=switch, number=number, reply=command)
        wait_uptime(
            client, session, switch, number, before_ns, dispatch, options, "reboot"
        )
        wait_healthy(client, session, switch, number, items, options, "reboot")


def wait_uptime(
    client: NetworkaClient,
    session: lab.Session,
    switch: str,
    number: int,
    before_ns: int,
    dispatch: Mapping[str, Any],
    options: Mapping[str, Any],
    operation: str,
) -> None:
    port = client.devices[switch].port or client.config.general.port
    while True:
        time.sleep(POLL_S)
        if not _ssh_ready(session.lab.node(switch).address, port):
            continue
        reading = routeros.collect_uptime(client, switch, **options)
        observed = session.mark(
            f"{operation}_uptime", switch=switch, number=number, uptime=reading
        )
        try:
            after_ns = routeros.uptime_ns(reading)
        except ValueError:
            continue
        if _restarted(before_ns, after_ns, observed["mono_ns"] - dispatch["mono_ns"]):
            return


def wait_healthy(
    client: NetworkaClient,
    session: lab.Session,
    target: str,
    number: int,
    items: list[intent.IntentItem],
    options: Mapping[str, Any],
    operation: str,
) -> None:
    attempt = 0
    while True:
        attempt += 1
        directory = session.directory / "recovery" / str(number) / str(attempt)
        health = intent.run_intent(client, items, directory, **options)
        session.mark(
            f"{operation}_health",
            switch=target,
            number=number,
            attempt=attempt,
            verdict=health.verdict,
        )
        if health.verdict == "pass":
            return
        time.sleep(POLL_S)


def uptime_proof(
    events: Sequence[Mapping[str, Any]],
    before: int,
    start: Mapping[str, Any],
    switch: str,
    number: int,
    operation: str,
) -> tuple[int, int]:
    for probe in events:
        if (
            probe["name"] != f"{operation}_uptime"
            or probe.get("number") != number
            or probe.get("switch") != switch
        ):
            continue
        try:
            after = routeros.uptime_ns(probe["uptime"])
        except ValueError:
            continue
        elapsed = probe["mono_ns"] - start["mono_ns"]
        if _restarted(before, after, elapsed):
            return after, elapsed
    msg = "The recorded uptime does not prove a new boot."
    raise ValueError(msg)


def health_proof(
    folder: Path,
    events: Sequence[Mapping[str, Any]],
    target: str,
    number: int,
    items: list[intent.IntentItem],
    operation: str,
) -> Mapping[str, Any]:
    health = [
        e
        for e in events
        if e["name"] == f"{operation}_health"
        and e.get("number") == number
        and e.get("switch") == target
    ][-1]
    attempt = int(health["attempt"])
    path = folder / "recovery" / str(number) / str(attempt) / intent.EVIDENCE_FILE
    recovered = intent.replay_intent(items, intent.load_json(path.read_text()))
    return {**health, "verdict": recovered.verdict}


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
        after, elapsed_ns = uptime_proof(own, before, start, switch, number, "reboot")
        result.update(after_uptime_s=after / NS, elapsed_s=elapsed_ns / NS)
        health = health_proof(folder, own, switch, number, items, "reboot")
        elapsed = (health["mono_ns"] - start["mono_ns"]) / NS
        result.update(healthy_s=elapsed, state=health["verdict"])
        if not result["elapsed_s"] <= elapsed <= wait_s or health["verdict"] != "pass":
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
