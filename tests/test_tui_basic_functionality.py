from __future__ import annotations

from pathlib import Path

from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.sequence_manager import SequenceManager
from network_toolkit.tui.data import TuiData


def test_tui_targets_are_sorted_and_unique(mock_repo_config: Path) -> None:
    data = TuiData(str(mock_repo_config))
    t = data.targets()

    # Devices
    assert t.devices == sorted(t.devices)
    assert len(t.devices) == len(set(t.devices))

    # Groups
    assert t.groups == sorted(t.groups)
    assert len(t.groups) == len(set(t.groups))


def test_tui_actions_sequences_sorted_unique_and_non_empty(
    mock_repo_config: Path,
) -> None:
    data = TuiData(str(mock_repo_config))
    a = data.actions()

    assert a.sequences == sorted(a.sequences)
    assert len(a.sequences) == len(set(a.sequences))
    assert "" not in a.sequences


def test_tui_default_constructor_discovers_repo_config(mock_repo_config: Path) -> None:
    assert TuiData().targets().devices == ["router1", "switch1"]


def test_actions_contain_known_vendor_sequence_and_resolve(
    mock_repo_config: Path,
) -> None:
    cfg: NetworkConfig = load_config(str(mock_repo_config))
    data = TuiData(str(mock_repo_config))
    sm = SequenceManager(cfg)

    actions = set(data.actions().sequences)
    vendor_seqs = sm.list_vendor_sequences("mikrotik_routeros")

    # The TUI actions list should include known vendor sequences
    assert "system_info" in vendor_seqs
    assert "system_info" in actions

    # And it should resolve to non-empty commands for that device
    resolved = data.sequence_commands("system_info", "router1")
    assert resolved is not None
    assert "/system/identity/print" in resolved


def test_tui_sequence_resolution_matches_sequence_manager_for_vendor(
    mock_repo_config: Path,
) -> None:
    cfg: NetworkConfig = load_config(str(mock_repo_config))
    sm = SequenceManager(cfg)
    data = TuiData(str(mock_repo_config))

    vendor_seqs = sm.list_vendor_sequences("cisco_iosxe")
    tui_cmds = data.sequence_commands("system_info", "switch1")
    assert tui_cmds == vendor_seqs["system_info"].commands


def test_tui_sequence_commands_unknown_returns_none(mock_repo_config: Path) -> None:
    data = TuiData(str(mock_repo_config))
    unknown = "__no_such_sequence__"
    assert data.sequence_commands(unknown, None) is None
