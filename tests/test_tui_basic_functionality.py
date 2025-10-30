from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.sequence_manager import SequenceManager
from network_toolkit.tui.data import TuiData

# Get the repository root directory (parent of tests directory)
REPO_ROOT = Path(__file__).parent.parent
CONFIG_DIR = REPO_ROOT / "config"


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
    # TuiData() uses default path; load_config falls back to modular config
    data = TuiData(str(mock_repo_config))
    assert len(data.targets().devices) > 0


def _first_device_with_vendor(
    cfg: NetworkConfig, vendor: str
) -> tuple[str, Any] | None:
    if not cfg.devices:
        return None
    for name, dev in cfg.devices.items():
        if getattr(dev, "device_type", None) == vendor:
            return name, dev
    return None


@pytest.mark.parametrize("vendor,known_seq", [("mikrotik_routeros", "system_info")])
def test_actions_contain_known_vendor_sequence_and_resolve(
    vendor: str, known_seq: str, mock_repo_config: Path
) -> None:
    cfg: NetworkConfig = load_config(str(mock_repo_config))
    data = TuiData(str(mock_repo_config))
    sm = SequenceManager(cfg)

    # Ensure repo actually has the vendor; otherwise skip gracefully
    dev_pair = _first_device_with_vendor(cfg, vendor)
    if dev_pair is None:
        pytest.skip(f"No device with vendor {vendor} in test config")
    device_name, _ = dev_pair

    actions = set(data.actions().sequences)
    vendor_seqs = sm.list_vendor_sequences(vendor)

    # The TUI actions list should include known vendor sequences
    assert known_seq in vendor_seqs, f"Expected {known_seq} provided for {vendor}"
    assert known_seq in actions

    # And it should resolve to non-empty commands for that device
    resolved = data.sequence_commands(known_seq, device_name)
    assert resolved and all(isinstance(c, str) and c for c in resolved)


def test_tui_sequence_resolution_matches_sequence_manager_for_vendor(
    mock_repo_config: Path,
) -> None:
    cfg: NetworkConfig = load_config(str(mock_repo_config))
    sm = SequenceManager(cfg)
    data = TuiData(str(mock_repo_config))

    # Find any device and use its vendor
    assert cfg.devices, "Expected devices in config"
    device_name, dev = next(iter(cfg.devices.items()))
    vendor = dev.device_type

    vendor_seqs = sm.list_vendor_sequences(vendor)
    if not vendor_seqs:
        pytest.skip(f"No vendor sequences found for {vendor}")

    # Compare commands for a sample sequence
    seq_name, rec = next(iter(vendor_seqs.items()))
    expected_cmds = list(rec.commands)
    tui_cmds = data.sequence_commands(seq_name, device_name)
    assert tui_cmds == expected_cmds


def test_tui_sequence_commands_unknown_returns_none(mock_repo_config: Path) -> None:
    data = TuiData(str(mock_repo_config))
    unknown = "__no_such_sequence__"
    assert data.sequence_commands(unknown, None) is None
