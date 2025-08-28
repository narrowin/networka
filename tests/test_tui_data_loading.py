from __future__ import annotations

from pathlib import Path

from network_toolkit.tui.data import TuiData


def test_tui_data_loads_from_config_dir(mock_repo_config: Path) -> None:
    """Test TUI data loading with proper test config directory."""
    data = TuiData(str(mock_repo_config))
    targets = data.targets()
    actions = data.actions()

    # Basic sanity: our test config has devices, groups, and vendor sequences
    assert len(targets.devices) > 0, (
        "Expected devices to be discovered from config/devices/*.yml"
    )
    assert len(targets.groups) > 0, (
        "Expected groups to be discovered from config/groups/*.yml"
    )
    assert len(actions.sequences) > 0, (
        "Expected sequences to be discovered from config/sequences/**/*.yml"
    )
