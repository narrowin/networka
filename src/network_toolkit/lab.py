"""Access to a deployed containerlab lab from the lab host.

The module reads the lab directory that containerlab writes, runs commands in a
node's network namespace, starts packet captures and ping streams, and sets a
cable down or up. It needs root on the lab host, next to
containerlab. It knows nothing about the devices in the lab.

A capture point is written `node:interface`. `node` is the containerlab node
name and `interface` is the interface name inside the node's network
namespace, for example `client1:bond0` or `switch1:tap2`.

Every action is written to `events.jsonl` with its epoch and monotonic time.
"""

from __future__ import annotations

import itertools
import json
import os
import signal
import socket
import subprocess
import threading
import time
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple

from network_toolkit import traffic
from network_toolkit.exceptions import NetworkToolkitError

TOPOLOGY_DATA = "topology-data.json"
# Local namespace commands, tcpdump startup, and child shutdown normally take milliseconds.
LOCAL_TIMEOUT_S = 5.0
# A veth changes carrier within milliseconds, so 1 s is ample to see the far end follow.
CONFIRM_TIMEOUT_S = 1.0
# The QEMU monitor answers on the loopback within milliseconds, so 3 s only catches a hung one.
QMP_TIMEOUT_S = 3.0


class LabError(NetworkToolkitError):
    """The lab cannot be reached, or an action on it failed."""


class Point(NamedTuple):
    """A capture point or link endpoint: a node and an interface in its namespace."""

    node: str
    interface: str

    def __str__(self) -> str:
        return f"{self.node}:{self.interface}"


@dataclass(frozen=True)
class Node:
    """One containerlab node: its name, kind, container name and management address."""

    name: str
    kind: str
    container: str
    address: str


@dataclass(frozen=True)
class Qemu:
    """The QEMU NIC behind one container interface of a node that runs in QEMU."""

    pid: int
    nic: str
    tap: str
    qmp_host: str
    qmp_port: int


def point(text: str) -> Point:
    """Parse `node:interface`."""
    node, _, interface = text.partition(":")
    if not node or not interface:
        msg = f"a capture point is written node:interface, not {text!r}"
        raise LabError(msg)
    return Point(node, interface)


def run(command: list[str], timeout: float = LOCAL_TIMEOUT_S) -> str:
    """Run one command and return its output; a failure raises LabError."""
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=True
        )
    except subprocess.CalledProcessError as error:
        msg = f"{' '.join(command)} failed: {error.stderr.strip() or error.returncode}"
        raise LabError(msg) from error
    except (OSError, subprocess.TimeoutExpired) as error:
        msg = f"{' '.join(command)} failed: {error}"
        raise LabError(msg) from error
    return done.stdout


@dataclass(frozen=True)
class Lab:
    """A containerlab lab: its nodes, its links and, once loaded, the container PIDs."""

    name: str
    nodes: Mapping[str, Node]
    links: tuple[tuple[Point, Point], ...]
    pids: Mapping[str, int] = field(default_factory=dict)

    def node(self, name: str) -> Node:
        if name not in self.nodes:
            msg = f"lab {self.name} has no node {name!r}"
            raise LabError(msg)
        return self.nodes[name]

    def peer(self, end: Point) -> Point:
        """The other end of the link that has `end` as one endpoint."""
        for a, z in self.links:
            if end == a:
                return z
            if end == z:
                return a
        msg = f"{end} is not a link endpoint in lab {self.name}"
        raise LabError(msg)

    def ns(self, node: str, *command: str) -> list[str]:
        """`command` prefixed to run in the network namespace of `node`."""
        self.node(node)
        return ["nsenter", "-t", str(self.pids[node]), "-n", *command]

    def run(self, node: str, *command: str) -> str:
        return run(self.ns(node, *command))

    def link_state(self, end: Point) -> dict[str, Any]:
        """`ip -j -d link show` of one interface in its node's namespace."""
        return json.loads(
            self.run(end.node, "ip", "-j", "-d", "link", "show", "dev", end.interface)
        )[0]

    def ipv4(self, end: Point) -> str:
        """The first IPv4 address of one interface in its node's namespace."""
        found = json.loads(
            self.run(end.node, "ip", "-j", "-4", "addr", "show", "dev", end.interface)
        )
        for entry in found:
            for address in entry.get("addr_info", []):
                if address.get("family") == "inet":
                    return str(address["local"])
        msg = f"{end} has no IPv4 address"
        raise LabError(msg)

    def qemu(self, end: Point) -> Qemu | None:
        """The QEMU NIC behind `end`, or None when the node runs no QEMU.

        The container interface and the QEMU TAP must share one bridge in the
        node's namespace, and the TAP must be the netdev of exactly one QEMU NIC.
        Anything else raises LabError, so a QEMU monitor action never hits the
        wrong cable.
        """
        pid = qemu_process(self.pids[end.node])
        if pid is None:
            return None
        args = Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0")
        netdevs, devices, qmp = qemu_layout(args)
        master = self.link_state(end).get("master")
        members = []
        if master:
            listed = json.loads(
                self.run(end.node, "ip", "-j", "link", "show", "master", master)
            )
            members = [m["ifname"] for m in listed if m["ifname"] in netdevs.values()]
        nics = [
            devices[i] for i, tap in netdevs.items() if tap in members and i in devices
        ]
        if len(members) != 1 or len(nics) != 1 or qmp is None:
            msg = (
                f"cannot tell which QEMU NIC is behind {end}: bridge {master!r} "
                f"holds TAPs {members}, NICs {nics}, QEMU monitor {qmp}"
            )
            raise LabError(msg)
        return Qemu(pid, nics[0], members[0], *qmp)


def parse_topology(data: Mapping[str, Any]) -> Lab:
    """The nodes and links of a containerlab `topology-data.json`."""
    try:
        nodes = {
            name: Node(
                name,
                str(node["kind"]),
                str(node["longname"]),
                str(node.get("mgmt-ipv4-address", "")),
            )
            for name, node in data["nodes"].items()
        }
        links = tuple(
            (
                Point(
                    link["endpoints"]["a"]["node"], link["endpoints"]["a"]["interface"]
                ),
                Point(
                    link["endpoints"]["z"]["node"], link["endpoints"]["z"]["interface"]
                ),
            )
            for link in data.get("links", [])
        )
        return Lab(str(data["name"]), nodes, links)
    except (KeyError, TypeError, AttributeError) as error:
        msg = f"{TOPOLOGY_DATA} lacks the expected field {error}"
        raise LabError(msg) from error


def load_lab(directory: Path) -> Lab:
    """Load a deployed lab from its lab directory, the `clab-<name>/` folder.

    The process must be root, and every node's container must run.
    """
    if os.geteuid() != 0:
        msg = "lab tests need root on the lab host to enter node namespaces and capture"
        raise LabError(msg)
    data = Path(directory) / TOPOLOGY_DATA
    if not data.is_file():
        msg = f"no deployed containerlab lab in {directory}: {TOPOLOGY_DATA} is missing"
        raise LabError(msg)
    lab = parse_topology(json.loads(data.read_text()))
    template = '{{.Name}} {{.State.Running}} {{.State.Pid}} {{index .Config.Labels "containerlab"}}'
    containers = [node.container for node in lab.nodes.values()]
    try:
        lines = run(
            ["docker", "inspect", "--format", template, *containers]
        ).splitlines()
    except LabError as error:
        msg = f"lab {lab.name} is not deployed: {error.message}"
        raise LabError(msg) from error
    pids = {}
    for node, line in zip(lab.nodes.values(), lines, strict=True):
        name, running, pid, owner = line.split(" ", 3)
        if name.lstrip("/") != node.container or running != "true" or owner != lab.name:
            msg = f"lab {lab.name} is not deployed: container {node.container} is not running in it"
            raise LabError(msg)
        pids[node.name] = int(pid)
    return replace(lab, pids=pids)


def qemu_process(container_pid: int) -> int | None:
    """The PID of the one QEMU process in the network namespace of a container."""
    netns = os.readlink(f"/proc/{container_pid}/ns/net")
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if os.readlink(entry / "ns" / "net") != netns:
                continue
            program = (entry / "cmdline").read_bytes().split(b"\0")[0]
        except OSError:
            continue
        if Path(program.decode()).name.startswith("qemu-system-"):
            found.append(int(entry.name))
    if len(found) > 1:
        msg = f"container PID {container_pid} runs {len(found)} QEMU processes"
        raise LabError(msg)
    return found[0] if found else None


def qemu_layout(
    args: list[str],
) -> tuple[dict[str, str], dict[str, str], tuple[str, int] | None]:
    """TAP per netdev id, NIC id per netdev id, and the first TCP QEMU monitor."""
    netdevs, devices, qmp = {}, {}, None
    for flag, value in itertools.pairwise(args):
        options = dict(part.split("=", 1) for part in value.split(",") if "=" in part)
        if flag == "-netdev" and value.startswith("tap,") and "ifname" in options:
            netdevs[options["id"]] = options["ifname"]
        elif flag == "-device" and "netdev" in options and "id" in options:
            devices[options["netdev"]] = options["id"]
        elif flag == "-qmp" and qmp is None and value.startswith("tcp:"):
            host, port = value.split(",")[0].removeprefix("tcp:").rsplit(":", 1)
            qmp = (host, int(port))
    return netdevs, devices, qmp


def qmp_command(
    qemu: Qemu, command: str, arguments: Mapping[str, Any]
) -> dict[str, Any]:
    """Send one command to the QEMU monitor inside the node's network namespace.

    A new thread enters the namespace, so the caller's namespace stays the same.
    """
    reply: Future[dict[str, Any]] = Future()

    def exchange() -> None:
        if not reply.set_running_or_notify_cancel():
            return
        try:
            with open(f"/proc/{qemu.pid}/ns/net") as netns:
                os.setns(netns.fileno(), os.CLONE_NEWNET)  # type: ignore[attr-defined]
            result = qmp_exchange(qemu.qmp_host, qemu.qmp_port, command, arguments)
        except BaseException as error:
            reply.set_exception(error)
        else:
            reply.set_result(result)

    worker = threading.Thread(target=exchange)
    try:
        worker.start()
        return reply.result()
    except BaseException as error:
        if not reply.cancel():
            # A deadline or Ctrl-C interrupts the caller, not the QMP worker.
            # Drain the command before cleanup can send an inverse operation.
            while not reply.done():
                with suppress(BaseException):
                    reply.exception()
        if isinstance(error, Exception):
            msg = f"QEMU monitor {command} on NIC {qemu.nic} failed: {error}"
            raise LabError(msg) from error
        raise


def qmp_exchange(
    host: str, port: int, command: str, arguments: Mapping[str, Any]
) -> dict[str, Any]:
    with (
        socket.create_connection((host, port), timeout=QMP_TIMEOUT_S) as conn,
        conn.makefile("rwb") as stream,
    ):
        if "QMP" not in json.loads(stream.readline()):
            msg = "invalid QEMU monitor greeting"
            raise LabError(msg)
        action = {"execute": command, "arguments": dict(arguments), "id": 2}
        for request in ({"execute": "qmp_capabilities", "id": 1}, action):
            started = time.time_ns()
            stream.write((json.dumps(request) + "\n").encode())
            stream.flush()
            while True:
                reply = json.loads(stream.readline())
                if reply.get("id") == request["id"]:
                    break
            if "return" not in reply:
                msg = f"QEMU rejected {request['execute']}: {reply}"
                raise LabError(msg)
    return {
        "started_ns": started,
        "done_ns": time.time_ns(),
        "request": action,
        "reply": reply,
    }


def file_name(end: Point) -> str:
    return f"{end.node}-{end.interface}"


@dataclass
class Process:
    kind: str
    name: str
    child: subprocess.Popen[bytes]
    log: Path


class Session:
    """Captures, streams and cable changes of one test run, saved in one directory.

    The directory gets `captures/` with one pcap and tcpdump log per capture
    point, `streams/` with one ping log per stream, and `events.jsonl`. Use it
    as a context manager: on leaving, also after an error or Ctrl-C, every
    process is stopped and every cable it set down is set up again.
    """

    def __init__(self, lab: Lab, directory: Path) -> None:
        self.lab = lab
        self.directory = Path(directory)
        for sub in ("captures", "streams"):
            (self.directory / sub).mkdir(parents=True, exist_ok=True)
        self.processes: list[Process] = []
        self.down: set[Point] = set()
        self.repairs: dict[Point, int] = {}
        self.restore_errors: list[str] = []
        self.stopped: dict[str, Any] | None = None
        self.start_clock = (time.time_ns(), time.monotonic_ns())

    def __enter__(self) -> Session:
        return self

    def __exit__(
        self, _kind: object, original: BaseException | None, _traceback: object
    ) -> None:
        try:
            self.stop()
        except Exception as error:
            self.record_restore_errors([f"stopping lab session: {error}"], original)

    def record_restore_errors(
        self, errors: list[str], original: BaseException | None
    ) -> None:
        """Retain cleanup failures while allowing the first action error to propagate."""
        self.restore_errors.extend(errors)
        if errors and original is None:
            raise LabError("; ".join(errors))

    def mark(self, name: str, **data: Any) -> dict[str, Any]:
        """Append one event with its epoch and monotonic time to events.jsonl."""
        event = {
            "name": name,
            "epoch_ns": time.time_ns(),
            "mono_ns": time.monotonic_ns(),
            **data,
        }
        with (self.directory / "events.jsonl").open("a") as file:
            file.write(json.dumps(event) + "\n")
        return event

    def launch(self, kind: str, name: str, command: list[str], log: Path) -> Process:
        with log.open("wb") as output:
            child = subprocess.Popen(
                command,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                # Capture readiness and kernel drop counts use tcpdump's English output.
                env={**os.environ, "LC_ALL": "C"},
            )
        process = Process(kind, name, child, log)
        self.processes.append(process)
        return process

    def start_captures(self, points: list[str]) -> dict[str, Path]:
        """Start tcpdump at every capture point, then wait once until all listen.

        `-U --immediate-mode` writes each packet when it arrives, so a stop
        loses no buffered tail and a pcap can be read while it is written.
        Returns the pcap path per capture point.
        """
        started: dict[str, tuple[Process, Path]] = {}
        for where in points:
            end = point(where)
            pcap = self.directory / "captures" / f"{file_name(end)}.pcap"
            command = self.lab.ns(
                end.node,
                "tcpdump",
                "-U",
                "--immediate-mode",
                "-i",
                end.interface,
                "-w",
                str(pcap),
            )
            log = pcap.with_suffix(".log")
            started[str(end)] = (self.launch("capture", str(end), command, log), pcap)
        deadline = time.monotonic() + LOCAL_TIMEOUT_S
        waiting = dict(started)
        while waiting:
            for where, (process, pcap) in list(waiting.items()):
                if "listening on" in process.log.read_text(errors="replace"):
                    del waiting[where]
                    self.mark(
                        "capture_started",
                        point=where,
                        pcap=str(pcap.relative_to(self.directory)),
                    )
                elif process.child.poll() is not None or time.monotonic() > deadline:
                    text = process.log.read_text(errors="replace").strip()
                    msg = f"capture at {where} did not start: {text}"
                    raise LabError(msg)
            # Poll twice per ping interval so a ready capture starts measuring promptly.
            time.sleep(traffic.INTERVAL_NS / (2 * traffic.NS))
        return {where: pcap for where, (_, pcap) in started.items()}

    def start_stream(
        self,
        ident: int,
        name: str,
        source: str,
        destination: str,
        interval_s: float,
        *,
        address: str | None = None,
        broadcast: bool = False,
    ) -> Path:
        """Start a ping from `source` to the IPv4 address of `destination`; return its log.

        `ident` is the ICMP identifier that tells the pings of this stream apart.
        """
        start = point(source)
        target = address or self.lab.ipv4(point(destination))
        log = self.directory / "streams" / f"{name}.log"
        command = self.lab.ns(
            start.node,
            "ping",
            "-n",
            "-D",
            "-O",
            *(("-b",) if broadcast else ()),
            "-i",
            str(interval_s),
            "-e",
            str(ident),
            "-I",
            start.interface,
            target,
        )
        self.launch("stream", name, command, log)
        self.mark(
            "stream_started",
            stream=name,
            ident=ident,
            source=str(start),
            destination=destination,
            address=target,
            log=str(log.relative_to(self.directory)),
        )
        return log

    def set_link(self, where: str, state: str) -> dict[str, Any]:
        """Set the cable with endpoint `where` down or up.

        An end on a node that runs in QEMU gets the change on its container
        interface and on its QEMU NIC through the QEMU monitor, because the guest
        sees a carrier change only that way. When no end runs in QEMU, both
        container interfaces change. The carrier is then confirmed at each end
        the engine did not set itself, the far end. Returns the `link_observed`
        event.
        """
        if state not in ("down", "up"):
            msg = f"a cable state is down or up, not {state!r}"
            raise LabError(msg)
        up = state == "up"
        first = point(where)
        ends = (first, self.lab.peer(first))
        qemu = {end: nic for end in ends if (nic := self.lab.qemu(end)) is not None}
        changed = [end for end in ends if end in qemu] or list(ends)
        far = [end for end in ends if end not in changed]
        if not up:
            self.down.add(first)
        self.mark(
            "link_start", point=str(first), state=state, ends=[str(e) for e in ends]
        )
        with ThreadPoolExecutor(max_workers=len(changed) + len(qemu)) as jobs:
            linux = [
                jobs.submit(
                    self.lab.run,
                    end.node,
                    "ip",
                    "link",
                    "set",
                    "dev",
                    end.interface,
                    state,
                )
                for end in changed
            ]
            guest = {
                end: jobs.submit(
                    qmp_command, nic, "set_link", {"name": nic.nic, "up": up}
                )
                for end, nic in qemu.items()
            }
            every: list[Future[Any]] = [*linux, *guest.values()]
            errors = [job.exception() for job in every if job.exception()]
            replies = {
                str(end): job.result()
                for end, job in guest.items()
                if not job.exception()
            }
        applied = self.mark(
            "link_applied",
            point=str(first),
            state=state,
            ip_link=[str(e) for e in changed],
            qmp=replies,
            errors=[str(e) for e in errors],
        )
        if errors:
            raise LabError(str(errors[0])) from errors[0]
        seen: dict[str, int] = {}
        flags: dict[str, list[str]] = {}
        deadline = time.monotonic() + CONFIRM_TIMEOUT_S
        while len(seen) < len(far) and time.monotonic() < deadline:
            for end in far:
                flags[str(end)] = self.lab.link_state(end)["flags"]
                if ("LOWER_UP" in flags[str(end)]) == up:
                    seen.setdefault(str(end), time.monotonic_ns())
            if len(seen) < len(far):
                # Check carrier several times per 100 ms ping interval.
                time.sleep(0.03)
        confirmed = len(seen) == len(far)
        observed = self.mark(
            "link_observed",
            point=str(first),
            state=state,
            far=[str(e) for e in far],
            flags=flags,
            latency_s=(max(seen.values()) - applied["mono_ns"]) / 1e9
            if seen and confirmed
            else None,
            confirmed=confirmed,
        )
        if not confirmed:
            msg = f"carrier of {first} is not {state} at the far end after {CONFIRM_TIMEOUT_S:g} s: {flags}"
            raise LabError(msg)
        if up:
            self.down.discard(first)
        return observed

    def stop(self) -> dict[str, Any]:
        """Stop every process and record any cable that could not be set up again.

        A second call returns the first result.
        """
        if self.stopped is not None:
            return self.stopped
        for end in sorted(self.down):
            try:
                started = self.mark("repair_start", point=str(end))
                self.set_link(str(end), "up")
                self.repairs[end] = started["epoch_ns"]
            except Exception as error:
                self.restore_errors.append(f"{end}: {error}")
        early = [p.name for p in self.processes if p.child.poll() is not None]
        for kind in ("stream", "capture"):
            group = [p for p in self.processes if p.kind == kind]
            if kind == "stream" and group:
                self.mark("stream_cutoff")
            for process in group:
                if process.child.poll() is None:
                    process.child.send_signal(signal.SIGINT)
            for process in group:
                try:
                    process.child.wait(timeout=LOCAL_TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    process.child.kill()
                    process.child.wait()
            if kind == "stream" and group:
                # Capture replies for the final requests through their delivery deadline.
                time.sleep(traffic.LATE_REPLY_NS / traffic.NS)
        epoch, mono = self.start_clock
        self.stopped = self.mark(
            "stopped",
            early_exits=early,
            restore_errors=list(self.restore_errors),
            clock_delta_ns=(time.time_ns() - epoch) - (time.monotonic_ns() - mono),
        )
        return self.stopped
