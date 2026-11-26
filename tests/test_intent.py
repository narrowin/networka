"""Tests for the vendor-neutral intent checks and the Linux bonding normalizer."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from network_toolkit import intent
from network_toolkit.api.run import DeviceCommandResult
from network_toolkit.cli import app
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms.linux.intent import bonding, check_bond_member
from network_toolkit.platforms.mikrotik_routeros import intent as ros

BOND = """Active Aggregator Info:
\tAggregator ID: 2

Slave Interface: eth1
MII Status: up
Aggregator ID: 2
details actor lacp pdu:
    system priority: 65535
    system mac address: 02:00:00:11:00:12
    port state: 63
details partner lacp pdu:
    system priority: 65535
    system mac address: 52:54:00:E1:0B:03
    port state: 71

Slave Interface: eth2
MII Status: down
Aggregator ID: 1
details actor lacp pdu:
    port state: 63
details partner lacp pdu:
    port state: 63
"""
EVIDENCE = {"bond": {"command": bonding("bond0"), "output": BOND, "error": None}}


def test_platform_lookup_names_supported_platforms() -> None:
    with pytest.raises(
        NetworkToolkitError, match="supported: linux, mikrotik_routeros"
    ):
        intent.platform("cisco_ios")


def test_linux_lacp_member_and_partner_system() -> None:
    scd = {"synchronization": True, "collecting": True, "distributing": True}
    result = intent.check_lacp_member(EVIDENCE, "linux", "bond0", "eth1", scd)
    assert result.verdict == "mismatch"
    assert result.observed["partner"] == {
        "synchronization": False,
        "collecting": False,
        "distributing": False,
    }
    system = {"priority": 65535, "mac": "52:54:00:e1:0b:03"}
    assert intent.check_lacp_partner_system(
        EVIDENCE, "linux", "bond0", "eth1", system
    ).verdict == ("match")


def test_linux_bond_member() -> None:
    expected = {"carrier": True, "eligible": True}
    result = check_bond_member(EVIDENCE, "bond0", "eth2", expected)
    assert result.observed == {"carrier": False, "eligible": False}
    missing = check_bond_member(EVIDENCE, "bond0", "eth3", expected)
    assert missing.reason == "expected one section for eth3, found 0"


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
  check: version
  params: {}
  expected: 7.26beta7
"""


def _routeros_client() -> MagicMock:
    replies = {
        ros.bridge_monitor(
            "bridge"
        ): '{"mlag-state":"connected","mlag-active-role":"primary"}',
        ros.PORT_STATS: "[]",
        ros.bond_monitor("client2"): (
            '[{"port":"ether4","flags":"ATGSCD--","partner-sys-id":"02:00:00:11:00:12",'
            '"partner-sys-priority":65535,"partner-flags":"ATGSCD--"}]'
        ),
        ros.RESOURCE: '{"version":"7.26beta7 (testing)"}',
    }
    client = MagicMock()
    client.devices = {"r1": MagicMock(device_type="mikrotik_routeros")}
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
    live = intent.run_intent(_routeros_client(), items, tmp_path / "out", source)
    replayed = intent.replay_directory(tmp_path / "out")
    assert live.verdict == "pass"
    assert [r for _, r in live.results] == [r for _, r in replayed.results]
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "evidence.json",
        "intent.yaml",
    ]
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
        "- {device: r1, check: bond_member, params: {bond: b, member: m}, expected: {}}\n"
    )
    with pytest.raises(
        intent.IntentError, match="only for linux, not mikrotik_routeros"
    ):
        intent.run_intent(_routeros_client(), intent.load_intent(source))
