# Intent verification

Compare how a switch should be operating with what its read-only commands
report. Each check returns the expected value, the observed value, and a
verdict, and replays from saved evidence without the device.

## How the checks are split

A check compares one concept, such as MLAG peer state, with the value you
expect. The code is split along what is shared and what is not:

- `network_toolkit.intent` holds `Reply`, `IntentResult` and the neutral
  checks. A neutral check compares normalized fields and never sees command
  text.
- `network_toolkit.platforms.<platform>.intent` holds the collectors, which
  read through `NetworkaClient.run` and keep every reply as `command`,
  `output` and `error`, and the normalizers, which turn saved evidence into
  the neutral fields. Checks that only make sense on one platform live there
  too.

`intent.platform(device_type)` returns the module for a Networka device type
and names the supported platforms for any other. Each check takes the device
type and looks up its normalizer the same way.

Every result carries `expected`, `observed`, `verdict` and `reason`.
Equality is **match** and a difference is **mismatch**. A read error, a reply
for another command, an absent or ambiguous object, or a missing field is
**unavailable**, and `reason` says why. Saved evidence replays to the same
verdict without the device.

## Check a switch

```python
import json
from pathlib import Path

from network_toolkit import NetworkaClient, intent

with NetworkaClient() as client:
    device_type = client.devices["dc1-core-mlag1"].device_type
    evidence = intent.platform(device_type).collect_bridge(
        client, "dc1-core-mlag1", "bridge"
    )
Path("bridge.json").write_text(json.dumps(evidence))

result = intent.check_mlag(
    evidence, device_type, "bridge", {"connected": True, "role": "primary"}
)
print(result.expected, result.observed, result.verdict, result.reason)
```

Collectors record a read failure in the evidence instead of raising. Extra
keyword arguments go to `NetworkaClient.run`, for example `interactive_creds`.
Evidence from several collectors can be merged into one dictionary.

## Neutral checks

Only the fields named in `expected` are compared, so one check covers, for
example, both the root bridge ID and the root port.

| Check | Normalized fields | Example `expected` |
| --- | --- | --- |
| `check_bridge_port` | `forwarding`, `role` (`root`, `designated`, `alternate`, `backup`, `disabled`), `edge` | `{"forwarding": True, "edge": True}` |
| `check_bridge_port_forwarding` | `forwarding` | `expected=True` |
| `check_bridge_ports` | Ports of the bridge, as a sorted list | `{"ether2", "client1", "client2"}` |
| `check_stp_bridge` | `bridge_id`, `root_bridge_id` (`0xPPPP.mac` in lower case), `root_bridge`, `root_port` (`None` on the root), `topology_changes` | `{"root_bridge_id": "0x1000.52:54:00:e1:0b:01", "root_port": "uplink"}` |
| `check_stp_mode` | Spanning-tree protocol, `none` when off | `"rstp"` |
| `check_mlag` | `connected`, `role` (`primary`, `secondary`), `state` (the platform's own word) | `{"connected": True, "role": "secondary"}` |
| `check_lacp_member` | LACP flags of the actor and the partner: `activity`, `timeout`, `aggregation`, `synchronization`, `collecting`, `distributing`, `defaulted`, `expired` | `{"synchronization": True, "collecting": True, "distributing": True}` |
| `check_lacp_partner_system` | LACP system `priority` and `mac` the partner sends | `{"priority": 65535, "mac": "02:00:00:11:00:12"}` |
| `check_host_entry` | Port of the bridge host entry for a MAC, `None` without one | `"client2"` |
| `check_interface_up` | Carrier | `expected=True` |
| `check_rebooted` | Uptime of a later reading is lower than an earlier one | `expected=True` |

`check_lacp_member` matches when both the actor and the partner side equal
`expected`. Both MLAG peers must present one LACP system ID, so
`check_lacp_partner_system` gives the same value for each member of an MLAG
bond when it is read on the partner.

The normalizers are public, for example
`intent.platform("mikrotik_routeros").mlag(evidence, "bridge")`, for reports
that record a value over time rather than check it.

## Platform-specific checks

| Platform | Check | Why it is not neutral |
| --- | --- | --- |
| RouterOS | `check_property(evidence, menu, where, name, expected)` | Compares one property of a `print detail` entry, for example `pvid`, `edge`, `bpdu-guard`, `loop-protect`, `lacp-strict` or `mlag-priority`. These are RouterOS configuration names. |
| RouterOS | `check_version(evidence, expected)` | Compares the version of `/system resource print`. The expected value comes from a RouterOS image name, so the format is RouterOS's own. |
| RouterOS | `check_bridge_port_forwarding(evidence, bridge, interface, expected)` | The native JSON form of the neutral forwarding check, kept with its signature. |
| Linux | `check_bond_member(evidence, bond, member, expected)` | Compares the bonding driver's `carrier` (MII Status) and `eligible`: the member is in the active aggregator and both port states are synchronized, collecting and distributing. Aggregator selection is a Linux bonding concept. |

## Platform support

| Check | `mikrotik_routeros` | `linux` |
| --- | --- | --- |
| `check_bridge_port`, `check_bridge_port_forwarding` | Native JSON from `collect_bridge_port`, or the port monitor text | No |
| `check_bridge_ports`, `check_stp_bridge`, `check_mlag` | Bridge and port monitor text from `collect_bridge` | No |
| `check_stp_mode` | Bridge print from `collect_stp_mode` | No |
| `check_lacp_member`, `check_lacp_partner_system` | Bonding monitor from `collect_bond` | `/proc/net/bonding/<bond>` from `collect_bond` |
| `check_host_entry` | Bridge host print from `collect_host_entry` | No |
| `check_interface_up` | Ethernet monitor from `collect_interface` | No |
| `check_rebooted` | Uptime from `collect_uptime` | No |

### RouterOS evidence

The bridge-port reply of `collect_bridge_port` is native JSON: the
statistics row whose `bridge` and `interface` match gives the `.id` for the
monitor command, and the monitor reply must carry the same `.id`. The other
collectors keep the CLI text of the commands the module builds, for example
`bridge_monitor("bridge")`. `collect(client, device, *commands)` runs several
of them joined with `;` as one read, which keeps readings that belong
together from one moment. A normalizer accepts a joined reply, and each
value it needs must then appear once in the output. The port monitor table
is read by column, so a blank cell of an inactive port is left out instead of
shifting the cells that follow it. `/interface/bridge/monitor` and
`/interface bridge monitor` count as the same command.

### Cumulus Linux

Cumulus Linux bonds use the Linux bonding driver, so the `linux` normalizer
reads their `/proc/net/bonding/<bond>` as it is. The table below plans how
the other concepts map to Cumulus output, from the commands the NVIDIA guides
describe and from [draft PR #47](#validate-cumulus-in-the-lab). None of it
has been checked against a switch, and no Cumulus module exists yet.

| Neutral fields | Cumulus source | Maps cleanly |
| --- | --- | --- |
| Bridge port `forwarding` | `bridge -j link show dev <port>`, `state` is `forwarding` | Yes |
| Bridge port `role`, `edge` | `mstpctl showportdetail <bridge> <port>`, `role` and `oper edge port` | Yes |
| `check_bridge_ports` | `bridge -j link show`, ports whose `master` is the bridge | Yes |
| `check_stp_bridge` | `mstpctl showbridge <bridge>`: bridge ID, designated root, root port, topology change count | Partly: bridge IDs print as `8.000.mac` and need converting to `0xPPPP.mac` |
| `check_stp_mode` | `nv show bridge domain <bridge> stp` mode | Partly: `pvrst` has no RouterOS counterpart, and `none` is spanning tree switched off |
| `check_mlag` `connected`, `role` | `nv show mlag --output json`, peer alive and role | Partly: MLAG is not bridge-scoped on Cumulus, so the bridge argument does not select anything there |
| `check_mlag` `state` | None | No: the state word is each platform's own |
| `check_lacp_member`, `check_lacp_partner_system` | `/proc/net/bonding/<bond>` (the `linux` normalizer) | Yes |
| `check_host_entry` | `bridge -j fdb show br <bridge>`, `ifname` of the MAC | Yes |
| `check_interface_up` | `nv show interface --output json`, `link.oper-status` | Yes |
| `check_rebooted` | `/proc/uptime` | Yes |

### Add a platform

1. Create `src/network_toolkit/platforms/<device_type>/intent.py` with a
   collector per concept, for example `collect_bridge`, that keeps each
   reply through `intent.read`.
2. Add the normalizers it can support, with the names the neutral checks
   look up: `bridge_port`, `bridge_ports`, `stp_bridge`, `stp_mode`, `mlag`,
   `lacp_member`, `host_interface`, `interface_up` and `uptime_ns`. Each
   returns the neutral fields and raises `ValueError` when the evidence cannot
   decide. Leave out a field the platform does not report.
3. Add the module to `intent.PLATFORMS`. A check whose normalizer is missing
   names the platform and the normalizer.

For a live RouterOS match and an offline negative control of the bridge-port
check, see the [Medium MikroTik lab replay](examples/intent/README.md#medium-mikrotik-lab-replay).

## Run the archive example

From the Networka checkout, set `MLAG` to the local checkout of
`narrowin/mikrotik-mlag-testsuite`. The archive replay uses commit
`59299681efd9089e6bba5a008cb1e220bb94d19e`. The example runs in the Networka
project environment because it uses the library check.
[Archive details and additional examples](examples/intent/README.md).

```bash
MLAG=/absolute/path/to/mikrotik-mlag-testsuite
PYTHONPATH="$MLAG/src" uv run --locked python docs/examples/intent/compare.py "$MLAG"
```

## Validate Cumulus in the lab

The Cumulus selectors are provisional. Run this section from the Networka
checkout of [draft PR #47](https://github.com/narrowin/networka/pull/47),
using the `MLAG` checkout above.

```bash
gh pr checkout 47
```

Set `SWITCH` to the lab SSH target. Use the bridge, bond, and port names from
that lab. Save the version information and both successful JSON replies.

```bash
SWITCH=cumulus@leaf01
EVIDENCE=/absolute/path/to/cumulus-intent-capture
mkdir -p "$EVIDENCE"
ssh "$SWITCH" 'cat /etc/os-release' > "$EVIDENCE/os-release.txt"
ssh "$SWITCH" 'nv show interface --output json' > "$EVIDENCE/interfaces.json"
ssh "$SWITCH" 'bridge -j link show dev swp1' > "$EVIDENCE/bridge-swp1.json"
```

Replay both replies from the Networka checkout. Update the arguments if the
lab uses different object names.

```bash
PYTHONPATH="$MLAG/src" uv run --offline --no-project python docs/examples/intent/compare.py "$MLAG" \
  --cumulus-interface bond1 "$EVIDENCE/interfaces.json" \
  --cumulus-stp-port br_default swp1 "$EVIDENCE/bridge-swp1.json"
```

Cross-check the bond with `nv show interface bond1` and, for an STP bridge
managed by `mstpd`, the port with `sudo mstpctl showstpport br_default`.
Try a naturally down interface or a non-forwarding port if one is present.
`down`, `blocking`, `learning`, `listening`, and `disabled` give a mismatch in
their respective checks. Bond operational state and LACP member participation
are separate checks. [NVUE JSON output][nvue-cli] ·
[Published NVUE interface JSON shape][nvue-api] · [Cumulus STP guide][cumulus-stp] ·
[Linux bridge JSON implementation][iproute2-bridge].

### Check VLAN-specific spanning tree

On a lab bridge running PVRST, use the VLAN configured in the lab and capture
both forms. The first command is the operator reference. The second probes
whether the target release supports JSON for this view.

```bash
ssh "$SWITCH" 'nv show bridge domain br_default stp vlan 110' > "$EVIDENCE/stp-vlan110.txt"
ssh "$SWITCH" 'nv show bridge domain br_default stp vlan 110 --output json' \
  > "$EVIDENCE/stp-vlan110.json" 2> "$EVIDENCE/stp-vlan110.stderr"
```

Record the Cumulus version, observed field paths, and verdicts in PR #47.
Record command errors or differences between the kernel and daemon views as
well. The current bridge-port check covers port-wide forwarding. The VLAN
check needs a qualified VLAN-and-port selector before it can report a
verdict. [NVIDIA PVRST command reference][nvue-stp].

[nvue-cli]: https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-519/System-Configuration/NVIDIA-User-Experience-NVUE/NVUE-CLI/
[nvue-api]: https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-519/System-Configuration/NVIDIA-User-Experience-NVUE/NVUE-API/#use-filters-in-a-query
[cumulus-stp]: https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-519/Layer-2/Spanning-Tree-and-Rapid-Spanning-Tree/
[nvue-stp]: https://docs.nvidia.com/networking-ethernet-software/nvue-reference/Show-Commands/Bridge/#nv-show-bridge-domain-domain-id-stp-vlan-vid
[iproute2-bridge]: https://github.com/iproute2/iproute2/blob/main/bridge/link.c
