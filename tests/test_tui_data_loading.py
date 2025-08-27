from __future__ import annotations

from pathlib import Path

from network_toolkit.tui.data import TuiData

# Get the repository root directory (parent of tests directory)
REPO_ROOT = Path(__file__).parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def test_tui_data_loads_from_config_dir() -> None:
    data = TuiData(str(CONFIG_DIR))
    targets = data.targets()
    actions = data.actions()

    # Basic sanity: our repo has non-empty config/devices, config/groups, and vendor sequences
    assert len(targets.devices) > 0, (
        "Expected devices to be discovered from config/devices/*.yml"
    )
    assert len(targets.groups) > 0, (
        "Expected groups to be discovered from config/groups/*.yml"
    )
    assert len(actions.sequences) > 0, (
        "Expected sequences to be discovered from config/sequences/**/*.yml"
    )
