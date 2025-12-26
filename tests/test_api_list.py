"""Tests for list API."""

from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.api.list import (
    get_device_list,
    get_group_list,
    get_sequence_list,
)
from network_toolkit.config import NetworkConfig


@pytest.fixture
def mock_config():
    config = MagicMock(spec=NetworkConfig)

    # Mock devices
    dev1 = MagicMock()
    dev1.host = "192.168.1.1"
    dev1.device_type = "cisco_ios"
    dev1.description = "Core Switch"
    dev1.tags = ["core", "cisco"]

    dev2 = MagicMock()
    dev2.host = "192.168.1.2"
    dev2.device_type = "mikrotik_routeros"
    dev2.description = None
    dev2.tags = []

    config.devices = {"dev1": dev1, "dev2": dev2}

    # Mock groups
    group1 = MagicMock()
    group1.members = ["dev1"]
    group1.description = "Core Devices"
    group1.match_tags = ["core"]

    config.device_groups = {"group1": group1}

    config.get_transport_type.return_value = "ssh"

    return config


def test_get_device_list(mock_config):
    devices = get_device_list(mock_config)

    assert len(devices) == 2
    assert devices[0].name == "dev1"
    assert devices[0].hostname == "192.168.1.1"
    assert devices[0].groups == ["group1"]
    assert devices[0].description == "Core Switch"

    assert devices[1].name == "dev2"
    assert devices[1].groups == []


def test_get_group_list(mock_config):
    groups = get_group_list(mock_config)

    assert len(groups) == 1
    assert groups[0].name == "group1"
    assert groups[0].members == ["dev1"]
    assert groups[0].description == "Core Devices"


def test_get_sequence_list(mock_config):
    # Mock SequenceManager
    with patch("network_toolkit.api.list.SequenceManager") as mock_sm_cls:
        sm = mock_sm_cls.return_value

        seq1 = MagicMock()

        seq1.category = "maintenance"
        seq1.description = "Upgrade"
        seq1.source = "repo"
        seq1.commands = ["cmd1"]
        seq1.timeout = 30
        seq1.device_types = ["cisco_ios"]

        seq2 = MagicMock()
        seq2.category = "info"
        seq2.description = "Show info"
        seq2.source = "builtin"
        seq2.commands = ["cmd2"]
        seq2.timeout = None
        seq2.device_types = []

        sm.list_all_sequences.return_value = {
            "cisco_ios": {"upgrade": seq1},
            "mikrotik_routeros": {"info": seq2},
        }

        sequences = get_sequence_list(mock_config)

        assert len(sequences) == 2
        # Sorted by vendor then name. cisco_ios < mikrotik_routeros
        assert sequences[0].name == "upgrade"
        assert sequences[0].vendor == "cisco_ios"
        assert sequences[1].name == "info"
        assert sequences[1].vendor == "mikrotik_routeros"
