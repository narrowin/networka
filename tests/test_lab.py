"""Tests for the pure parts of the containerlab lab access."""

import pytest

from network_toolkit import lab

# A cut of the topology-data.json that containerlab 0.83 wrote for the Small MLAG lab.
TOPOLOGY = {
    "name": "mlag-small",
    "type": "clab",
    "nodes": {
        "dc1-core-mlag1": {
            "shortname": "dc1-core-mlag1",
            "longname": "clab-mlag-small-dc1-core-mlag1",
            "kind": "mikrotik_chr",
            "mgmt-ipv4-address": "172.30.215.11",
        },
        "dc1-traffic-host1": {
            "shortname": "dc1-traffic-host1",
            "longname": "clab-mlag-small-dc1-traffic-host1",
            "kind": "linux",
            "mgmt-ipv4-address": "172.30.215.16",
        },
    },
    "links": [
        {
            "endpoints": {
                "a": {
                    "node": "dc1-core-mlag1",
                    "interface": "eth2",
                    "mac": "aa:c1:ab:e7:ae:37",
                    "peer": "z",
                },
                "z": {
                    "node": "dc1-traffic-host1",
                    "interface": "eth1",
                    "mac": "aa:c1:ab:6d:26:54",
                    "peer": "a",
                },
            }
        }
    ],
}

# Arguments of the CHR's QEMU process in the Small lab, shortened.
QEMU_ARGS = [
    "/usr/bin/qemu-system-aarch64",
    "-qmp",
    "tcp:127.0.0.1:5001,server,nowait",
    "-qmp",
    "tcp:127.0.0.1:5002,server,nowait",
    "-netdev",
    "tap,id=mgmt,ifname=tap0,script=no,downscript=no",
    "-device",
    "virtio-net,netdev=mgmt,mac=52:54:00:da:0b:00",
    "-netdev",
    "tap,id=d2,ifname=tap2,script=no,downscript=no",
    "-device",
    "virtio-net,id=nic2,netdev=d2,mac=52:54:00:da:0b:02,speed=10000,duplex=full",
]


def test_parse_topology_reads_nodes_and_links() -> None:
    parsed = lab.parse_topology(TOPOLOGY)
    assert parsed.name == "mlag-small"
    assert parsed.nodes["dc1-traffic-host1"] == lab.Node(
        "dc1-traffic-host1",
        "linux",
        "clab-mlag-small-dc1-traffic-host1",
        "172.30.215.16",
    )
    end = lab.point("dc1-traffic-host1:eth1")
    assert parsed.peer(end) == lab.Point("dc1-core-mlag1", "eth2")
    assert str(parsed.peer(parsed.peer(end))) == "dc1-traffic-host1:eth1"


def test_peer_of_a_point_outside_the_links_fails() -> None:
    parsed = lab.parse_topology(TOPOLOGY)
    with pytest.raises(lab.LabError, match="not a link endpoint"):
        parsed.peer(lab.point("dc1-traffic-host1:bond0"))


def test_parse_topology_without_nodes_fails() -> None:
    with pytest.raises(lab.LabError, match="lacks the expected field 'nodes'"):
        lab.parse_topology({"name": "x"})


def test_point_needs_node_and_interface() -> None:
    with pytest.raises(lab.LabError, match="node:interface"):
        lab.point("dc1-traffic-host1")


def test_qemu_layout_maps_taps_to_nics_and_finds_the_monitor() -> None:
    netdevs, devices, qmp = lab.qemu_layout(QEMU_ARGS)
    assert netdevs == {"mgmt": "tap0", "d2": "tap2"}
    assert devices == {"d2": "nic2"}
    assert qmp == ("127.0.0.1", 5001)
