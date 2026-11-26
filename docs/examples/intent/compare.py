"""Compare selected operational facts from archived and published evidence."""

from __future__ import annotations

import argparse
import json
import re
from itertools import islice
from pathlib import Path

from mlag_lab.direct_topology import DIRECT_FLOWS
from mlag_lab.root_evidence import summarize_router

from network_toolkit import intent

POWER_CASE = Path("results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss")
BOND_CASE = Path("results/2026-11-24-small-search/mstp-default-l2/01-bond-member-loss")
PROBE_CASES = Path("results/2026-11-24-forwarding-checks/small-mstp-reboots")
ROUTEROS_LINK = "/interface ethernet monitor ether2 once"
ROUTEROS_MLAG = "/interface bridge monitor bridge once"
CUMULUS_INTERFACES = "nv show interface --output json"
CUMULUS_BRIDGE_PORT = "bridge -j link show dev {interface}"
CIST_ROOT = "0x1000.52:54:00:d7:0b:01"
JUNOS_COMMAND = "show interfaces terse | display json"
JUNOS_SOURCE = (
    "Juniper Day One: Automating Junos with Salt, pp. 58-59 (published excerpt)\n"
    "  https://www.juniper.net/documentation/en_US/day-one-books/"
    "DO_Automating_SALT.pdf#page=58"
)
# Only the selected row is projected from the printed, truncated JSON excerpt.
JUNOS_EXCERPT = """
{
  "interface-information": [{
    "physical-interface": [{
      "name": [{"data": "ge-0/0/0"}],
      "admin-status": [{"data": "up"}],
      "oper-status": [{"data": "up"}]
    }]
  }]
}
"""
ROUTEROS_LINK_STATES = {"link-ok": "up", "no-link": "down"}
JUNOS_LINK_STATES = {"up": "up", "down": "down"}
IntentValue = str | bool


def archived_router(case: Path, peer: str, line: int, heading: str) -> str | None:
    path = case / f"state-{peer}.jsonl"
    with path.open(encoding="utf-8") as archive:
        record = json.loads(next(islice(archive, line - 1, line)))
    source = f"{path}:{line} (started_ns={record['started_ns']})"
    print(f"{heading}\n  source: {source}")
    error = record.get("stderr") or record.get("error")
    raw = record.get("raw")
    if error or raw is None:
        print(
            f"  capture error: {(error or 'archive has no raw command output').rstrip()}"
        )
        return None
    return raw


def junos_scalar(row, field: str) -> str:
    (value,) = row[field]
    value = value["data"]
    if not isinstance(value, str) or not value:
        raise ValueError(field)
    return value


def junos_physical_row(raw: str, name: str):
    (information,) = json.loads(raw)["interface-information"]
    (row,) = (
        row
        for row in information["physical-interface"]
        if junos_scalar(row, "name") == name
    )
    return row


def show_intent(path: str, expected: IntentValue, actual: IntentValue | None) -> None:
    if actual is None:
        verdict = "unavailable"
    else:
        verdict = "match" if actual == expected else "mismatch"
    print(f"  {path:24} expected={expected!r} actual={actual!r} → {verdict}")


def show_link(
    native_expected: str, native_actual: str | None, link_states: dict[str, str]
) -> None:
    show_intent("native", native_expected, native_actual)
    translated = link_states.get(native_actual) if native_actual is not None else None
    if native_actual is not None and translated is None:
        print(f"  translation unavailable for native value {native_actual!r}")
    show_intent("translated", "up", translated)


def show_baseline(path: str, before: str | None, after: str | None) -> None:
    if before is None or after is None:
        verdict = "unavailable"
    else:
        verdict = "unchanged" if before == after else "changed"
    print(f"  {path:24} before={before!r} after={after!r} → {verdict}")


def compare_mlag(case: Path) -> None:
    power_samples = (
        ("before", "p2", 3),
        ("during", "p2", 17),
        ("recovered", "p2", 171),
        ("before", "p1", 3),
        ("during", "p1", 16),
        ("recovered", "p1", 68),
    )
    selected = {}
    for label, peer, line in power_samples:
        raw = archived_router(case, peer, line, f"RouterOS {peer}/ether2 {label}")
        state = summarize_router(raw) if raw is not None else {}
        print(f"  command: {ROUTEROS_LINK}")
        link = state.get("carrier", {}).get("ether2")
        bridge = state.get("bridge", {})
        selected[peer, label] = (
            link,
            bridge.get("mlag-state"),
            bridge.get("mlag-active-role"),
        )
        if link is None and raw is not None:
            print("  carrier status omitted from the parsed sample")
        show_link("link-ok", link, ROUTEROS_LINK_STATES)
        print(f"  command: {ROUTEROS_MLAG}")
        # The translated branch leaves these vendor-specific checks native.
        show_intent("MLAG state (both)", "connected", bridge.get("mlag-state"))
        role = bridge.get("mlag-active-role")
        show_intent(
            "MLAG active role (both)", "secondary" if peer == "p2" else "primary", role
        )
        if role is None and raw is not None:
            print("  mlag-active-role omitted from the parsed sample")
        print()

    for peer in ("p2", "p1"):
        before, before_state, before_role = selected[peer, "before"]
        before_link = ROUTEROS_LINK_STATES.get(before) if before is not None else None
        for label in ("during", "recovered"):
            print(f"Selected baseline change, RouterOS {peer} {label} (sources above)")
            after, after_state, after_role = selected[peer, label]
            show_baseline("ether2 native", before, after)
            after_link = ROUTEROS_LINK_STATES.get(after) if after is not None else None
            show_baseline("ether2 translated", before_link, after_link)
            show_baseline("MLAG state", before_state, after_state)
            show_baseline("MLAG active role", before_role, after_role)
            print()


def compare_published_link() -> None:
    print(f"Junos vMX-1/ge-0/0/0\n  source: {JUNOS_SOURCE}\n  command: {JUNOS_COMMAND}")
    try:
        row = junos_physical_row(JUNOS_EXCERPT, "ge-0/0/0")
        oper = junos_scalar(row, "oper-status")
    except (ValueError, KeyError, TypeError) as error:
        print(f"  Junos extraction failed: {error!r}")
        oper = None
    show_link("up", oper, JUNOS_LINK_STATES)
    print()


def check_routeros_port_json(bridge: str, interface: str, evidence_path: Path) -> None:
    print(f"RouterOS native JSON, {bridge}/{interface}\n  source: {evidence_path}")
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"  evidence unreadable: {error}")
        evidence = {}
    if not isinstance(evidence, dict):
        evidence = {}
    for key in ("stats", "monitor"):
        reply = evidence.get(key)
        if isinstance(reply, dict):
            print(f"  command: {reply.get('command')}")
    result = intent.check_bridge_port(
        evidence, "mikrotik_routeros", bridge, interface, {"forwarding": True}
    )
    if result.reason:
        print(f"  extraction failed: {result.reason}")
    observed = result.observed["forwarding"] if result.observed else None
    show_intent("Bridge-port forwarding", True, observed)
    print()


def check_cumulus_interface_json(interface: str, path: Path) -> None:
    print(f"Cumulus NVUE JSON (provisional), {interface}")
    print(f"  source: {path}\n  command: {CUMULUS_INTERFACES}")
    status = None
    try:
        interfaces = json.loads(path.read_text(encoding="utf-8"))
        observed = interfaces[interface]["link"]["oper-status"]
        if observed in ("up", "down"):
            status = observed
        else:
            print(f"  unsupported operational status: {observed!r}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"  extraction failed: {error}")
    show_intent("Operational status", "up", status)
    print()


def check_cumulus_bridge_port_json(bridge: str, interface: str, path: Path) -> None:
    print(f"Cumulus Linux bridge JSON (provisional), {bridge}/{interface}")
    print(
        f"  source: {path}\n  command: {CUMULUS_BRIDGE_PORT.format(interface=interface)}"
    )
    forwarding = None
    try:
        ports = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(ports, list) or any(
            not isinstance(row, dict) for row in ports
        ):
            msg = "expected an array of bridge port records"
            raise ValueError(msg)
        selected = [
            row
            for row in ports
            if row.get("master") == bridge and row.get("ifname") == interface
        ]
        if len(selected) != 1:
            msg = "expected exactly one port with this bridge and interface name"
            raise ValueError(msg)
        state = selected[0].get("state")
        if state in ("forwarding", "blocking", "learning", "listening", "disabled"):
            forwarding = state == "forwarding"
        else:
            print(f"  unsupported bridge port state: {state!r}")
    except (OSError, ValueError) as error:
        print(f"  extraction failed: {error}")
    show_intent("Bridge-port forwarding", True, forwarding)
    print()


def mstp_port_columns_complete(raw: str) -> bool:
    # The existing whitespace parser can shift columns when a port has a blank cell.
    columns = re.findall(r"^\s*(interface|role|forwarding):([^\n]*)", raw, re.M)
    widths = {field: len(values.split()) for field, values in columns}
    return (
        len(columns) == len(widths) == 3
        and widths["interface"] > 0
        and widths["role"] == widths["forwarding"] == widths["interface"]
    )


def check_bonds_and_tree(case: Path) -> None:
    baseline_members = []
    for label, peer, line in (
        ("before", "p1", 1),
        ("before", "p2", 1),
        ("during", "p1", 20),
    ):
        raw = archived_router(
            case, peer, line, f"RouterOS MSTP bond-member-loss {peer} {label}"
        )
        state = summarize_router(raw) if raw is not None else {}
        print(f"  member bindings: {case / f'config-{peer}.txt'}:54-66")
        for bond, member in (("client1", "ether3"), ("client2", "ether4")):
            flags = state.get("lacp", {}).get(member, {})
            actor = flags.get("actor", "")
            partner = flags.get("partner", "")
            eligibility = None
            if len(actor) == len(partner) == 8:
                eligibility = (
                    "eligible" if actor[3:6] == partner[3:6] == "SCD" else "ineligible"
                )
            print(f"  command: /interface/bonding/monitor-slaves bond={bond} once=yes")
            print(f"  {member} actor={actor or None!r} partner={partner or None!r}")
            show_intent(f"{bond}/{member}", "eligible", eligibility)
            if label == "before":
                baseline_members.append(eligibility)
        if peer == "p1":
            print("  command: /interface/ethernet/monitor ether3 once")
            show_intent(
                "ether3 carrier", "link-ok", state.get("carrier", {}).get("ether3")
            )
            print("  command: /interface/bridge/monitor bridge once")
            show_intent(
                "CIST root ID", CIST_ROOT, state.get("bridge", {}).get("root-bridge-id")
            )
            print(
                "  command: /interface/bridge/port/monitor [find where bridge=bridge] once"
            )
            port = {}
            if raw is not None:
                if mstp_port_columns_complete(raw):
                    port = state["ports"].get("client1", {})
                else:
                    print(
                        "  port columns incomplete; role and forwarding cannot be assigned safely"
                    )
            show_intent("client1 role", "designated-port", port.get("role"))
            show_intent("client1 forwarding", "yes", port.get("forwarding"))
        print()

    print(
        "All four configured client-bond members, before loss (p1 and p2 sources above)"
    )
    actual = None
    if "ineligible" in baseline_members:
        actual = "a member was ineligible"
    elif all(member == "eligible" for member in baseline_members):
        actual = "all eligible"
    show_intent("baseline LACP", "all eligible", actual)
    print()


def probe_result(flow, description: str, *, baseline: bool) -> tuple[str | None, str]:
    if not isinstance(flow, dict) or flow.get("description") != description:
        return None, "required flow row is missing or has a different direction"
    sent = flow.get("sent")
    missed = flow.get("baseline_missed" if baseline else "missed")
    mismatches = flow.get("capture_mismatches")
    if not isinstance(mismatches, list) or mismatches:
        return None, "endpoint capture agreement is unavailable"
    if not all(type(value) is int and value >= 0 for value in (sent, missed)):
        return None, "probe score fields are incomplete or invalid"
    if sent == 0 or missed > sent:
        return None, "no probes sent or misses exceed sends"
    if baseline:
        good = flow.get("baseline_good")
        if type(good) is not int or good < 0 or good + missed != sent:
            return None, "baseline scores do not account for the sends"
    if missed:
        return "probes missed", "the selected window records missed probes"
    return "all probes delivered", "no misses recorded and endpoint captures agree"


def read_probe_report(path: Path, case: str) -> dict:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"  report error: {error}")
        return {}
    if not isinstance(report, dict) or report.get("case") != case:
        print(f"  expected report for case {case!r}")
        return {}
    return report


def check_reachability(path: Path) -> None:
    print(
        f"Reachability between the bonded client endpoints on VLAN 110\n  source: {path}"
    )
    report = read_probe_report(path, "direct-baseline")
    flows = {}
    if (
        report.get("fault_executed") is False
        and report.get("status") in ("pass", "fail")
        and isinstance(report.get("flows"), dict)
    ):
        flows = report["flows"]
    else:
        print("  valid direct-baseline report unavailable")
    for flow_id in (101, 201):
        source, destination, address, direction = DIRECT_FLOWS[flow_id]
        actual, detail = probe_result(flows.get(str(flow_id)), direction, baseline=True)
        print(f"  flows[{flow_id}] {direction} ({source} → {destination}, {address})")
        print(f"  {detail}")
        show_intent("baseline ICMP", "all probes delivered", actual)
    print()


def show_interrupted_reachability(path: Path) -> None:
    print(f"Continuity during the interrupted secondary reboot\n  source: {path}")
    report = read_probe_report(path, "direct-reboot-secondary")
    status = report.get("status")
    print(f"  report status: {status!r}")
    for check in report.get("checks", []):
        if check.get("level") == "error" and check.get("ok") is False:
            print(f"  report error: {check.get('detail')}")
    phases = {
        phase.get("key"): phase.get("verdict") for phase in report.get("phases", [])
    }
    for key in ("withdrawal", "restoration"):
        print(f"  {key}: {phases.get(key)}")
    complete = (
        status in ("pass", "fail")
        and report.get("fault_executed") is True
        and all(
            phases.get(key) in ("pass", "fail") for key in ("withdrawal", "restoration")
        )
    )
    for flow_id in (101, 201):
        flow = report.get("flows", {}).get(str(flow_id), {})
        direction = DIRECT_FLOWS[flow_id][3]
        actual, detail = probe_result(flow, direction, baseline=False)
        print(f"  flows[{flow_id}] {direction}: {detail}")
        if not complete:
            print("  the complete reboot window is unavailable")
        show_intent(
            f"reboot ICMP {flow_id}",
            "all probes delivered",
            actual if complete else None,
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mlag_checkout", type=Path, help="pinned MLAG lab checkout")
    parser.add_argument(
        "--routeros-stp-port",
        nargs=3,
        metavar=("BRIDGE", "INTERFACE", "EVIDENCE_JSON"),
        help="also check bridge-port forwarding from evidence saved by collect_bridge_port",
    )
    parser.add_argument(
        "--cumulus-interface",
        action="append",
        nargs=2,
        metavar=("INTERFACE", "NVUE_JSON"),
        help="also check operational status from saved Cumulus NVUE interface JSON (provisional)",
    )
    parser.add_argument(
        "--cumulus-stp-port",
        action="append",
        nargs=3,
        metavar=("BRIDGE", "INTERFACE", "BRIDGE_JSON"),
        help="also check bridge-port forwarding from saved Cumulus Linux bridge JSON (provisional)",
    )
    args = parser.parse_args()
    root = args.mlag_checkout
    compare_mlag(root / POWER_CASE)
    compare_published_link()
    check_bonds_and_tree(root / BOND_CASE)
    check_reachability(root / PROBE_CASES / "01-baseline" / "result.json")
    show_interrupted_reachability(
        root / PROBE_CASES / "01-secondary-reboot" / "result.json"
    )
    if args.routeros_stp_port:
        bridge, interface, evidence = args.routeros_stp_port
        check_routeros_port_json(bridge, interface, Path(evidence))
    for interface, path in args.cumulus_interface or ():
        check_cumulus_interface_json(interface, Path(path))
    for bridge, interface, path in args.cumulus_stp_port or ():
        check_cumulus_bridge_port_json(bridge, interface, Path(path))


if __name__ == "__main__":
    main()
