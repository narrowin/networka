from network_toolkit.api.info import InfoOptions, get_info
from network_toolkit.config import (
    DeviceConfig,
    DeviceGroup,
    NetworkConfig,
    VendorSequence,
)


def test_get_info_targets() -> None:
    config = NetworkConfig(
        devices={
            "dev1": DeviceConfig(
                host="192.0.2.1", command_sequences={"owner_check": ["owner command"]}
            )
        },
        device_groups={
            "group1": DeviceGroup(description="Check devices", members=["dev1"])
        },
        global_command_sequences={
            "seq1": VendorSequence(
                description="Check health", commands=["global command"]
            )
        },
    )

    result = get_info(InfoOptions(targets="dev1,group1,seq1,unknown1", config=config))

    assert result.device_count == 1
    assert {target.name: target.type for target in result.targets} == {
        "dev1": "device",
        "group1": "group",
        "seq1": "sequence",
    }
    assert result.targets[2].sequence_records[0].commands == ["global command"]
    assert result.unknown_targets == ["unknown1"]

    scoped = get_info(InfoOptions(targets="owner_check", config=config, device="dev1"))
    record = scoped.targets[0].sequence_records[0]
    assert record.commands == ["owner command"]
    assert record.source and record.source.origin == "device"

    vendor = get_info(
        InfoOptions(targets="owner_check", config=config, vendor="mikrotik_routeros")
    )
    assert vendor.targets[0].sequence_records == []
    assert vendor.unknown_targets == []
