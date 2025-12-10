from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.api.info import InfoOptions, get_info
from network_toolkit.config import NetworkConfig


@pytest.fixture
def mock_config():
    config = MagicMock(spec=NetworkConfig)
    config.devices = {"dev1": MagicMock()}
    config.device_groups = {"group1": ["dev1"]}
    return config


@patch("network_toolkit.api.info.SequenceManager")
def test_get_info_targets(mock_sm_cls, mock_config):
    mock_sm = MagicMock()
    mock_sm_cls.return_value = mock_sm
    mock_sm.list_all_sequences.return_value = {"vendor1": ["seq1"]}

    options = InfoOptions(targets="dev1,group1,seq1,unknown1", config=mock_config)

    result = get_info(options)

    assert result.device_count == 1
    assert len(result.targets) == 3

    target_names = {t.name: t.type for t in result.targets}
    assert target_names["dev1"] == "device"
    assert target_names["group1"] == "group"
    assert target_names["seq1"] == "sequence"

    assert "unknown1" in result.unknown_targets
