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
    """SequenceManager with user layer disabled to test builtin only."""

    # Force user root to None so only builtin is loaded
    def _none(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(SequenceManager, "_user_sequences_root", _none)
    return SequenceManager(_DummyConfig())


def test_mikrotik_builtin_sequences_common(sm_isolated: SequenceManager) -> None:
    vendor = "mikrotik_routeros"
    seqs = sm_isolated.list_vendor_sequences(vendor)

    # New KISS 7-sequence set
    expected_names = {
        "system_info",
        "health_check",
        "interfaces",
        "routing",
        "backup_config",
        "firewall",
        "logs",
    }
    assert set(seqs.keys()) == expected_names

    # Verify system_info sequence
    assert seqs["system_info"].commands == [
        "/system/identity/print",
        "/system/resource/print",
        "/system/routerboard/print",
    ]

    # Verify health_check sequence
    assert seqs["health_check"].commands == [
        "/system/resource/print",
        "/system/health/print",
        "/log/print last 20",
    ]

    # Verify interfaces sequence
    assert seqs["interfaces"].commands == [
        "/interface/print",
        "/interface/print stats",
        "/ip/address/print",
    ]

    # Verify routing sequence
    assert seqs["routing"].commands == [
        "/ip/route/print",
        "/ip/neighbor/print",
    ]

    # Verify backup_config sequence
    assert seqs["backup_config"].commands == [
        "/export compact",
        "/system/backup/save",
    ]


def test_arista_builtin_sequences_common(sm_isolated: SequenceManager) -> None:
    vendor = "arista_eos"
    seqs = sm_isolated.list_vendor_sequences(vendor)

    # New KISS 7-sequence set
    expected_names = {
        "system_info",
        "health_check",
        "interfaces",
        "routing",
        "backup_config",
        "vlans",
        "logs",
    }
    assert set(seqs.keys()) == expected_names

    # Verify system_info sequence
    assert seqs["system_info"].commands == [
        "show version",
        "show inventory",
        "show environment all",
    ]

    # Verify health_check sequence
    assert seqs["health_check"].commands == [
        "show processes top once",
        "show system memory",
        "show logging last 10",
    ]

    # Verify routing sequence
    assert seqs["routing"].commands == [
        "show ip route",
        "show lldp neighbors",
        "show ip arp",
    ]

    # Verify backup_config sequence
    assert seqs["backup_config"].commands == [
        "show running-config",
        "show startup-config",
    ]
