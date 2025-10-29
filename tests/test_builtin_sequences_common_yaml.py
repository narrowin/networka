"""Validate builtin vendor common.yml sequences and commands.

This test ensures the packaged builtin sequences for MikroTik RouterOS (v7)
and Arista EOS are correctly formatted YAML, load via SequenceManager, and
contain exactly the five approved sequences with the expected commands.
"""

from __future__ import annotations

from typing import Any

import pytest

from network_toolkit.sequence_manager import SequenceManager


class _DummyConfig:
    """Minimal duck-typed config for SequenceManager.

    We disable repo and user sequences by monkeypatching the roots to None.
    """

    # Attributes consulted by SequenceManager during init/load
    vendor_platforms: dict[str, Any] | None = None
    vendor_sequences: list[str] | None = None
    global_command_sequences: dict[str, Any] | None = None
    devices: dict[str, Any] | None = None


@pytest.fixture()
def sm_isolated(monkeypatch: pytest.MonkeyPatch) -> SequenceManager:
    """SequenceManager with user/repo layers disabled to test builtin only."""

    # Force user and repo roots to None so only builtin is loaded
    def _none(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(SequenceManager, "_user_sequences_root", _none)
    monkeypatch.setattr(SequenceManager, "_repo_sequences_root", _none)
    return SequenceManager(_DummyConfig())


def test_mikrotik_builtin_sequences_common(sm_isolated: SequenceManager) -> None:
    vendor = "mikrotik_routeros"
    seqs = sm_isolated.list_vendor_sequences(vendor)

    expected_names = {
        "system_info",
        "health_check",
        "interface_status",
        "routing_info",
        "security_audit",
        "backup_config",
    }
    assert set(seqs.keys()) == expected_names

    assert seqs["system_info"].commands == [
        "/system/identity/print",
        "/system/resource/print",
        "/system/routerboard/print",
        "/system/clock/print",
        "/system/package/print",
    ]

    assert seqs["health_check"].commands == [
        "/system/resource/print",
        "/system/clock/print",
        "/interface/print detail",
        '/log/print where topics~"error|critical|warning"',
    ]

    assert seqs["interface_status"].commands == [
        "/interface/print detail",
        "/interface/ethernet/print detail",
        "/interface/ethernet/monitor [find] once",
    ]

    assert seqs["routing_info"].commands == [
        "/ip/route/print detail",
        "/routing/ospf/neighbor/print",
        "/routing/bgp/peer/print terse",
    ]

    assert seqs["security_audit"].commands == [
        "/user/print",
        "/user/group/print",
        "/ip/service/print",
        "/ip/firewall/filter/print",
        "/ip/firewall/nat/print",
        '/log/print where topics~"account|critical|error|warning"',
    ]


def test_arista_builtin_sequences_common(sm_isolated: SequenceManager) -> None:
    vendor = "arista_eos"
    seqs = sm_isolated.list_vendor_sequences(vendor)

    expected_names = {
        "system_info",
        "health_check",
        "interface_status",
        "routing_info",
        "security_audit",
        "backup_config",
    }
    assert set(seqs.keys()) == expected_names

    assert seqs["system_info"].commands == [
        "show version",
        "show inventory",
        "show clock",
        "show environment",
        "show processes top once",
    ]

    assert seqs["health_check"].commands == [
        "show processes top once",
        "show memory",
        "show clock",
        "show interfaces status",
        "show logging last 10",
    ]

    assert seqs["interface_status"].commands == [
        "show interfaces status",
        "show interfaces counters",
        "show interfaces description",
        "show interfaces transceiver details",
    ]

    assert seqs["routing_info"].commands == [
        "show ip route",
        "show ip ospf neighbor",
        "show ip bgp summary",
        "show bfd neighbors",
    ]

    assert seqs["security_audit"].commands == [
        "show running-config section username",
        "show aaa",
        "show ip access-lists",
        "show logging",
    ]
