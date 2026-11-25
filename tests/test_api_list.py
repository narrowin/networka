"""Tests for list API."""

from unittest.mock import MagicMock

import pytest

from network_toolkit.api.list import (
    get_device_list,
    get_group_list,
    get_sequence_list,
)
from network_toolkit.config import DeviceConfig, NetworkConfig, VendorSequence


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


def test_get_sequence_list() -> None:
    config = NetworkConfig(
        vendor_sequences={
            "cisco_iosxe": {
                "scope_check": VendorSequence(
                    description="Upgrade",
                    commands=["platform command"],
                    category="test_scope",
                    timeout=30,
                ),
            }
        },
        global_command_sequences={
            "scope_check": VendorSequence(
                description="Fallback",
                commands=["global command"],
                category="test_scope",
            ),
            "restricted_check": VendorSequence(
                description="Router health",
                commands=["router command"],
                category="test_scope",
                device_types=["mikrotik_routeros"],
            ),
        },
        devices={
            "rack_router": DeviceConfig(
                host="192.0.2.1", command_sequences={"owner_check": ["owner command"]}
            )
        },
    )

    sequences = get_sequence_list(config, vendor="cisco_iosxe", category="test_scope")
    assert [sequence.name for sequence in sequences] == ["scope_check"]
    winner = sequences[0]
    assert winner.vendor == "cisco_iosxe"
    assert winner.commands == ["platform command"]
    assert winner.timeout == 30
    assert winner.source and winner.source.origin == "repo"

    catalogue = get_sequence_list(config)
    assert any(
        sequence.name == "owner_check" and sequence.device == "rack_router"
        for sequence in catalogue
    )
    assert any(
        sequence.name == "scope_check" and sequence.vendor is None
        for sequence in catalogue
    )
