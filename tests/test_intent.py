"""Tests for the vendor-neutral intent checks and the Linux bonding normalizer."""

import pytest

from network_toolkit import intent
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms.linux.intent import bonding, check_bond_member

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
