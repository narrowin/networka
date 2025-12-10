from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.api.diff import DiffOptions, diff_targets
from network_toolkit.config import NetworkConfig


@pytest.fixture
def mock_config():
    config = MagicMock(spec=NetworkConfig)
    config.devices = {"dev1": MagicMock(), "dev2": MagicMock()}
    config.device_groups = {}
    config.get_group_members.return_value = []
    config.general = MagicMock()
    config.general.results_dir = "results"
    return config

@patch("network_toolkit.api.diff.DeviceSession")
def test_diff_device_to_device_config(mock_session_cls, mock_config, tmp_path):
    # Setup mocks
    session_mock = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = session_mock

    # Mock execute_command to return different configs
    session_mock.execute_command.side_effect = ["config A", "config B"]

    options = DiffOptions(
        targets="dev1,dev2",
        subject="config",
        config=mock_config,
        save_current=tmp_path
    )

    result = diff_targets(options)

    assert result.device_pair_diff is True
    assert len(result.results) == 1
    assert result.results[0].outcome.changed is True
    # The output is a unified diff, so it should contain the lines
    assert "-config A" in result.results[0].outcome.output
    assert "+config B" in result.results[0].outcome.output

@patch("network_toolkit.api.diff.DeviceSession")
def test_diff_baseline_config(mock_session_cls, mock_config, tmp_path):
    # Setup baseline file
    baseline_file = tmp_path / "dev1.rsc"
    baseline_file.write_text("config A", encoding="utf-8")

    # Setup mocks
    session_mock = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = session_mock
    session_mock.execute_command.return_value = "config B"

    options = DiffOptions(
        targets="dev1",
        subject="config",
        config=mock_config,
        baseline=tmp_path
    )

    result = diff_targets(options)

    assert result.device_pair_diff is False
    assert len(result.results) == 1
    assert result.results[0].device == "dev1"
    assert result.results[0].outcome.changed is True

@patch("network_toolkit.api.diff.DeviceSession")
def test_diff_baseline_no_change(mock_session_cls, mock_config, tmp_path):
    # Setup baseline file
    baseline_file = tmp_path / "dev1.rsc"
    baseline_file.write_text("config A", encoding="utf-8")

    # Setup mocks
    session_mock = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = session_mock
    session_mock.execute_command.return_value = "config A"

    options = DiffOptions(
        targets="dev1",
        subject="config",
        config=mock_config,
        baseline=tmp_path
    )

    result = diff_targets(options)

    assert result.results[0].outcome.changed is False
