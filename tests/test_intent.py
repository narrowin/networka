"""Tests for the vendor-neutral intent checks and the Linux bonding normalizer."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from network_toolkit import intent
from network_toolkit.api.run import DeviceCommandResult
from network_toolkit.cli import app
from network_toolkit.config import DeviceConfig, NetworkConfig
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms.linux.intent import (
    bond_link,
    bond_slaves,
    check_bond_member,
)
from network_toolkit.platforms.linux.intent import ping_command as lx_ping_command
from network_toolkit.platforms.mikrotik_routeros import intent as ros


def _bond_evidence(mode: str, info: dict | None, members: list) -> dict:
    """Replies of `ip -j -d link show` for bond0 and its members.

    The values are from iproute2 6.15 JSON read on two 802.3ad bonds over veth
    pairs, cut down to the fields the normalizers read.
    """
    data = {"mode": mode} | ({} if info is None else {"ad_info": info})
    bond = [{"ifname": "bond0", "linkinfo": {"info_kind": "bond", "info_data": data}}]
    rows = [
        {
            "ifname": name,
            "master": "bond0",
            "linkinfo": {
                "info_slave_kind": "bond",
                "info_slave_data": {"mii_status": mii}
                | (
                    {}
                    if aggregator is None
                    else {
                        "ad_aggregator_id": aggregator,
                        "ad_actor_oper_port_state": actor,
                        "ad_partner_oper_port_state": partner,
                    }
                ),
            },
        }
        for name, mii, aggregator, actor, partner in members
    ]
    return {
        command: {"command": command, "output": json.dumps(value), "error": None}
        for command, value in ((bond_link("bond0"), bond), (bond_slaves("bond0"), rows))
    }


# eth2 of a bond whose peer set eth2 down.
EVIDENCE = _bond_evidence(
    "802.3ad",
    {"aggregator": 1, "partner_mac": "BE:37:7E:E0:AD:FE"},
    [("eth1", "UP", 1, 63, 63), ("eth2", "DOWN", 1, 15, 55)],
)


def test_platform_lookup_names_supported_platforms() -> None:
    with pytest.raises(
        NetworkToolkitError, match="supported: linux, mikrotik_routeros"
    ):
        intent.platform("cisco_ios")


def test_linux_lacp_member_and_partner_system() -> None:
    scd = {"synchronization": True, "collecting": True, "distributing": True}
    result = intent.check_lacp_member(EVIDENCE, "linux", "bond0", "eth2", scd)
    assert result.verdict == "fail"
    assert result.observed["partner"] == {
        "synchronization": False,
        "collecting": True,
        "distributing": True,
    }
    system = {"mac": "be:37:7e:e0:ad:fe"}
    assert intent.check_lacp_partner_system(
        EVIDENCE, "linux", "bond0", "eth2", system
    ).verdict == ("pass")
    priority = intent.check_lacp_partner_system(
        EVIDENCE, "linux", "bond0", "eth2", {"priority": 65535}
    )
    assert priority.reason == "bond0 member eth2 partner has no priority"


def test_linux_bond_member() -> None:
    expected = {"carrier": True, "eligible": True}
    result = check_bond_member(EVIDENCE, "bond0", "eth2", expected)
    assert result.observed == {"carrier": False, "eligible": False}
    assert check_bond_member(EVIDENCE, "bond0", "eth1", expected).verdict == "pass"
    missing = check_bond_member(EVIDENCE, "bond0", "eth3", expected)
    assert missing.reason == "expected one member row for eth3, found 0"


INTENT = """
- name: p1 MLAG primary
  device: r1
  check: mlag
  params: {bridge: bridge}
  expected: {connected: true, role: primary}
- device: r1
  check: lacp_member
  params: {bond: client2, member: ether4}
  expected: {synchronization: true, collecting: true, distributing: true}
- device: r1
  check: stp_bridge
  params: {bridge: bridge}
  expected: {root_bridge: true}
- device: r1
  check: version
  expected: 7.26beta7
"""


def _routeros_client() -> MagicMock:
    replies = {
        ros.bridge_monitor(
            "bridge"
        ): '{".id":"*A","mlag-state":"connected","mlag-active-role":"primary","root-bridge":true}',
        ros.bridge_print("bridge"): '[{".id":"*A","name":"bridge"}]',
        ros.PORT_STATS: "[]",
        ros.bond_monitor("client2"): (
            '[{"port":"ether4","flags":"ATGSCD--","partner-sys-id":"02:00:00:11:00:12",'
            '"partner-sys-priority":65535,"partner-flags":"ATGSCD--","partner":true}]'
        ),
        ros.RESOURCE: '{"version":"7.26beta7 (testing)"}',
    }
    client = MagicMock()
    client.config = NetworkConfig(
        devices={"r1": DeviceConfig(host="192.0.2.1", device_type="mikrotik_routeros")}
    )
    client.run.side_effect = lambda device, command, **_: MagicMock(
        command_results=[
            DeviceCommandResult(
                device, command, "\n".join(replies[c] for c in command.split(";"))
            )
        ]
    )
    return client


def test_run_intent_saves_evidence_that_replays_to_the_same_results(
    tmp_path: Path,
) -> None:
    source = tmp_path / "intent.yaml"
    source.write_text(INTENT)
    items = intent.load_intent(source)
    live = intent.run_intent(_routeros_client(), items, tmp_path / "out")
    replayed = intent.replay_directory(tmp_path / "out")
    assert live.verdict == "pass"
    assert [r for _, r in live.results] == [r for _, r in replayed.results]
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "evidence.json",
        "intent.yaml",
        "results.json",
    ]
    evidence = json.loads((tmp_path / "out" / "evidence.json").read_text())
    readings = evidence["devices"]["r1"]["readings"]
    assert [r["reader"] for r in readings] == [
        "read_bridge",
        "read_bond",
        "read_version",
    ]
    results = json.loads((tmp_path / "out" / "results.json").read_text())
    assert results["verdict"] == "pass"
    assert results["items"][0]["name"] == "p1 MLAG primary"
    result = CliRunner().invoke(app, ["intent", "replay", str(tmp_path / "out")])
    assert result.exit_code == 0
    assert "Intent verdict: pass" in result.output


def test_load_intent_names_file_and_item(tmp_path: Path) -> None:
    source = tmp_path / "bad.yaml"
    source.write_text("- {device: r1, check: mlg, params: {}, expected: 1}\n")
    with pytest.raises(
        intent.IntentError, match=r"bad.yaml item 1: unknown check 'mlg'"
    ):
        intent.load_intent(source)
    source.write_text(
        "- {device: r1, check: bond_member, params: {bond: b, member: m}, expected: {carrier: true}}\n"
    )
    with pytest.raises(
        intent.IntentError, match="only for linux, not mikrotik_routeros"
    ):
        intent.run_intent(_routeros_client(), intent.load_intent(source))
    for line, message in (
        (
            "check: host_entry, params: {bridge: bridge, mac: 1}, expected: x",
            "quote it",
        ),
        (
            "check: mlag, params: {bridge: 'br;x'}, expected: {connected: true}",
            "bridge must",
        ),
        (
            "check: mlag, params: {bridge: b}, expected: {connected: 1}",
            "connected must",
        ),
    ):
        source.write_text(f"- {{device: r1, {line}}}\n")
        with pytest.raises(intent.IntentError, match=message):
            intent.load_intent(source)


def test_replay_of_malformed_evidence_is_error_and_exit_2(tmp_path: Path) -> None:
    (tmp_path / "intent.yaml").write_text(INTENT)
    evidence = {
        "devices": {"r1": {"device_type": "mikrotik_routeros", "readings": None}}
    }
    (tmp_path / "evidence.json").write_text(json.dumps(evidence))
    report = intent.replay_directory(tmp_path)
    assert report.verdict == "error"
    assert intent.same(True, True) and not intent.same(True, 1)
    assert not intent.same({"a": [False]}, {"a": [0]})
    result = CliRunner().invoke(app, ["intent", "replay", str(tmp_path / "missing")])
    assert result.exit_code == 2
    assert "Traceback" not in result.output


PING_TEXT = """PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data.
64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=0.051 ms
64 bytes from 10.0.0.1: icmp_seq=3 ttl=64 time=0.058 ms

--- 10.0.0.1 ping statistics ---
3 packets transmitted, 2 received, 33.3333% packet loss, time 2042ms
rtt min/avg/max/mdev = 0.051/0.054/0.058/0.003 ms
"""


def test_linux_ping() -> None:
    command = lx_ping_command("10.0.0.1", 3)
    evidence = {command: {"command": command, "output": PING_TEXT, "error": None}}
    result = intent.check_ping(
        evidence, "linux", "10.0.0.1", 3, None, {"reachable": True}
    )
    assert (result.observed, result.verdict) == ({"reachable": False}, "fail")
    other = lx_ping_command("10.0.0.2", 3)
    wrong = {other: {"command": other, "output": PING_TEXT, "error": None}}
    assert intent.check_ping(
        wrong, "linux", "10.0.0.2", 3, None, {"received": 2}
    ).verdict == ("error")


def test_linux_bond_members() -> None:
    result = intent.check_bond_members(EVIDENCE, "linux", "bond0", ["eth1"])
    assert (result.observed, result.verdict) == (["eth1", "eth2"], "fail")
    other = json.loads(EVIDENCE[bond_slaves("bond0")]["output"])
    other[0]["master"] = "bond1"
    wrong = EVIDENCE | {
        bond_slaves("bond0"): EVIDENCE[bond_slaves("bond0")]
        | {"output": json.dumps(other)}
    }
    assert intent.check_bond_members(wrong, "linux", "bond0", []).reason == (
        "a member row does not name its port and master bond0"
    )


def test_linux_partner_gone_and_not_lacp() -> None:
    # The peer's bond0 was deleted: eth1 left the active aggregator 1.
    gone = _bond_evidence(
        "802.3ad",
        {"aggregator": 1, "partner_mac": "00:00:00:00:00:00"},
        [("eth1", "UP", 2, 71, 0), ("eth2", "UP", 1, 79, 0)],
    )
    scd = {"synchronization": True}
    result = intent.check_lacp_member(gone, "linux", "bond0", "eth2", scd)
    assert (result.verdict, result.observed["partner"]) == (
        "fail",
        {"synchronization": False},
    )
    mac = {"mac": "be:37:7e:e0:ad:fe"}
    assert intent.check_lacp_partner_system(
        gone, "linux", "bond0", "eth2", mac
    ).observed == {"mac": "00:00:00:00:00:00"}
    outside = intent.check_lacp_partner_system(gone, "linux", "bond0", "eth1", mac)
    assert (outside.verdict, outside.reason) == (
        "error",
        "bond0 member eth1 partner has no mac",
    )
    backup = _bond_evidence("active-backup", None, [("eth1", "UP", None, 0, 0)])
    assert intent.check_lacp_member(backup, "linux", "bond0", "eth1", scd).reason == (
        "bond0 is not an 802.3ad (LACP) bond"
    )
    assert intent.check_bond_members(backup, "linux", "bond0", ["eth1"]).verdict == (
        "pass"
    )
