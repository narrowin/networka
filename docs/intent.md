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

## Check a switch with an intent file

An intent file is a YAML list. Each item names a `device` from the Networka
inventory, a `check` from the tables below, its `params` and the `expected`
value. `name` and `source` are optional labels. Any other key, an unknown
check, params that do not fit the check, a device that is not in the
inventory, or a check its platform does not support is an error that names
the file and the item.

```yaml
- name: mlag1 is MLAG primary
  device: dc1-core-mlag1
  check: mlag
  params: {bridge: bridge}
  expected: {connected: true, role: primary}
- name: client2 bond member in use
  device: dc1-core-mlag1
  check: lacp_member
  params: {bond: client2, member: ether4}
  expected: {synchronization: true, collecting: true, distributing: true}
- name: host port has BPDU guard
  device: dc1-core-mlag1
  check: property
  params: {menu: /interface/bridge/port, where: {interface: ether4}, name: bpdu-guard}
  expected: true
```

Run it against the devices and save the evidence, then check the saved
evidence again without the devices:

```bash
nw intent run intent.yaml --save saved
nw intent replay saved
```

`--save` writes two files. `intent.yaml` is a copy of the intent file.
`evidence.json` holds one entry per item, in item order, with the `device`,
its `device_type`, the `check` and the replies its collector read, each as
`command`, `output` and `error`:

```json
{
  "items": [
    {
      "device": "dc1-core-mlag1",
      "device_type": "mikrotik_routeros",
      "check": "mlag",
      "evidence": {
        ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/monitor bridge once as-value]]": {
          "command": ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/monitor bridge once as-value]]",
          "output": "{\"mlag-state\":\"connected\",\"mlag-active-role\":\"primary\"}",
          "error": null
        }
      }
    }
  ]
}
```

Both commands print the same table, shortened here. In this example the
partner of `ether4` does not report the member as synchronized, collecting
and distributing:

```text
Item                       Device          Check        Expected                                  Observed                                         Verdict
mlag1 is MLAG primary      dc1-core-mlag1  mlag         {"connected": true, "role": "primary"}    {"connected": true, "role": "primary"}           match
client2 bond member in use dc1-core-mlag1  lacp_member  {"collecting": true, "distributing": true, {"actor": {"collecting": true, ...},             mismatch
                                                        "synchronization": true}                  "partner": {"collecting": false, ...}}
host port has BPDU guard   dc1-core-mlag1  property     true                                      true                                             match
Intent verdict: fail
```

The intent verdict is **fail** when any item is a mismatch, **unverified**
when no item is a mismatch but at least one is unavailable, and **pass**
otherwise. The exit status is 0 for pass, 1 for fail and 2 for unverified
or for an unusable intent file or evidence.

The same is available in Python. `run_intent` reads every item and then
evaluates the collected evidence exactly as `replay_intent` does, so a
replay of saved evidence gives the same results:

```python
from network_toolkit import NetworkaClient, intent

items = intent.load_intent("intent.yaml")
with NetworkaClient() as client:
    report = intent.run_intent(client, items, save_dir="saved", source="intent.yaml")
print(report.verdict)
for item, result in report.results:
    print(item.name, result.expected, result.observed, result.verdict, result.reason)

assert intent.replay_directory("saved").results == report.results
```

`run_intent` passes extra keyword arguments to `NetworkaClient.run`, for
example `interactive_creds`. `replay_intent(items, evidence)` takes the
content of `evidence.json` directly. The checks reach devices only through
their collectors, which record a read failure in the evidence instead of
raising, and the single checks can also be called on their own, as below.

## Check a single item

```python
from network_toolkit import NetworkaClient, intent

with NetworkaClient() as client:
    device_type = client.devices["dc1-core-mlag1"].device_type
    evidence = intent.platform(device_type).collect_bridge(
        client, "dc1-core-mlag1", "bridge"
    )
result = intent.check_mlag(
    evidence, device_type, "bridge", {"connected": True, "role": "primary"}
)
```

## Neutral checks

Only the fields named in `expected` are compared, so one check covers, for
example, both the root bridge ID and the root port. The intent file names a
check without its `check_` prefix: `check_mlag` is `mlag`.

| Check | `params` | Normalized fields | Example `expected` |
| --- | --- | --- | --- |
| `check_bridge_port` | `bridge`, `port` | `forwarding`, `role` (`root`, `designated`, `alternate`, `backup`, `disabled`), `edge` | `{"forwarding": true, "edge": true}` |
| `check_bridge_port_forwarding` | `bridge`, `port` | `forwarding` | `true` |
| `check_bridge_ports` | `bridge` | Ports of the bridge, as a sorted list | `["client1", "client2", "ether2"]` |
| `check_stp_bridge` | `bridge` | `bridge_id`, `root_bridge_id` (`0xPPPP.mac` in lower case), `root_bridge`, `root_port` (`null` on the root), `topology_changes` | `{"root_bridge_id": "0x1000.52:54:00:e1:0b:01", "root_port": "uplink"}` |
| `check_stp_mode` | `bridge` | Spanning-tree protocol, `none` when off | `"rstp"` |
| `check_mlag` | `bridge` | `connected`, `role` (`primary`, `secondary`), `state` (the platform's own word) | `{"connected": true, "role": "secondary"}` |
| `check_lacp_member` | `bond`, `member` | LACP flags of the actor and the partner: `activity`, `timeout`, `aggregation`, `synchronization`, `collecting`, `distributing`, `defaulted`, `expired` | `{"synchronization": true, "collecting": true, "distributing": true}` |
| `check_lacp_partner_system` | `bond`, `member` | LACP system `priority` and `mac` the partner sends | `{"priority": 65535, "mac": "02:00:00:11:00:12"}` |
| `check_host_entry` | `bridge`, `mac` | Port of the bridge host entry for a MAC, `null` without one | `"client2"` |
| `check_interface_up` | `interface` | Carrier | `true` |
| `check_rebooted` | Two readings; Python only | Uptime of a later reading is lower than an earlier one | `True` |

`check_lacp_member` matches when both the actor and the partner side equal
`expected`. Both MLAG peers must present one LACP system ID, so
`check_lacp_partner_system` gives the same value for each member of an MLAG
bond when it is read on the partner. `check_rebooted` compares two readings
taken at different times, so it has no intent file form.

The normalizers are public, for example
`intent.platform("mikrotik_routeros").mlag(evidence, "bridge")`, for reports
that record a value over time rather than check it.

## Platform-specific checks

| Platform | Check (`check` in a file) | `params` | Why it is not neutral |
| --- | --- | --- | --- |
| RouterOS | `check_property` (`property`) | `menu` in slash form, `where`, `name` | Compares one property of a menu entry, for example `pvid`, `edge`, `bpdu-guard`, `loop-protect`, `lacp-strict` or `mlag-priority`. These are RouterOS configuration names. Values compare as JSON, so `yes` is `true` and `110` is a number. |
| RouterOS | `check_version` (`version`) | none | Compares the version of the system resource without the channel. The expected value comes from a RouterOS image name, so the format is RouterOS's own. |
| RouterOS | `check_bridge_port_forwarding(evidence, bridge, interface, expected)` | Python only | The neutral forwarding check with its earlier RouterOS signature. |
| Linux | `check_bond_member` (`bond_member`) | `bond`, `member` | Compares the bonding driver's `carrier` (MII Status) and `eligible`: the member is in the active aggregator and both port states are synchronized, collecting and distributing. Aggregator selection is a Linux bonding concept. |

## Platform support

| Check | `mikrotik_routeros` | `linux` |
| --- | --- | --- |
| `bridge_port`, `bridge_port_forwarding` | Port statistics and monitor from `collect_bridge_port` | No |
| `bridge_ports`, `stp_bridge`, `mlag` | Bridge monitor and port statistics from `collect_bridge` | No |
| `stp_mode` | Bridge print from `collect_stp_mode` | No |
| `lacp_member`, `lacp_partner_system` | Bonding monitor from `collect_bond` | `/proc/net/bonding/<bond>` from `collect_bond` |
| `host_entry` | Bridge host print from `collect_host_entry` | No |
| `interface_up` | Ethernet monitor from `collect_interface` | No |
| `check_rebooted` | Uptime from `collect_uptime` | No |

### RouterOS evidence

Every RouterOS reply is native JSON. The module wraps each command as
`:put [:serialize to=json options=json.no-string-conversion [<command> as-value]]`,
so `yes` and `no` arrive as Booleans and numbers as numbers, and no CLI text
is parsed. The uptime is read as `:tonsec` of the system resource uptime.
`collect(client, device, *commands)` runs several commands joined with `;` as
one read, which keeps readings that belong together from one moment. Each
command prints one JSON line, so the collector splits the output into one
reply per command. For a bridge port, the statistics row whose `bridge` and
`interface` match gives the `.id` for the monitor command, and the monitor
reply must carry the same `.id`.

| Collector | Command inside the JSON wrapper | Checked on a device |
| --- | --- | --- |
| `collect_bridge_port`, `collect_bridge` | `/interface/bridge/port/print stats as-value`, `/interface/bridge/port/monitor <id> once as-value` | Yes, RouterOS CHR 7.20.6, 7.24.5 and 7.26beta7 |
| `collect_bridge` | `/interface/bridge/monitor <bridge> once as-value` | Not yet |
| `collect_bond` | `/interface/bonding/monitor-slaves bond=<bond> once as-value` | Not yet |
| `collect_interface` | `/interface/ethernet/monitor <interface> once as-value` | Not yet |
| `collect_host_entry` | `/interface/bridge/host/print as-value where mac-address=<mac>` | Not yet |
| `collect_stp_mode` | `/interface/bridge/print as-value where name=<bridge>` | Not yet |
| `collect_print` | `<menu>/print as-value` | Not yet |
| `collect_version` | `/system/resource/print as-value` | Not yet |
| `collect_uptime` | `:put [:serialize to=json [:tonsec [/system/resource/get uptime]]]` | Not yet |

The field names the normalizers read are the ones RouterOS prints for these
commands, for example `mlag-state`, `partner-flags` and `on-interface`. The
commands marked "Not yet" have not been run against a device, so their JSON
shape is still to be confirmed.

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
   collector per concept, with the names in `intent.CHECKS`, for example
   `collect_bridge`. Read the device's JSON output where it has one and keep
   each reply through `intent.read`.
2. Add the normalizers it can support, with the names the neutral checks
   look up: `bridge_port`, `bridge_ports`, `stp_bridge`, `stp_mode`, `mlag`,
   `lacp_member`, `host_interface`, `interface_up` and `uptime_ns`. Each
   returns the neutral fields and raises `ValueError` when the evidence cannot
   decide. Leave out a field the platform does not report.
3. Put the platform's own checks in a `CHECKS` dictionary of
   `intent.Check` entries, so intent files can name them. Use an empty
   dictionary when there are none.
4. Add the module to `intent.PLATFORMS`. An intent item whose collector or
   normalizer is missing on that platform is an error naming the item.

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
