# Intent verification

## Problem

A network test needs to know whether each switch is in the state it should
be in: MLAG peers connected with the right roles, LACP members in use, bridge
ports forwarding, spanning tree rooted where planned. Each project used to
read and parse device output itself, per vendor, and kept no evidence that a
later run could check again. Networka now describes the intended state in one
file, reads the devices once, saves what they returned, and checks the saved
evidence the same way live and offline.

## Design decisions

| Decision | Alternative considered | Why |
| --- | --- | --- |
| Collection and evaluation are separate. Collectors only read and save replies; checks only compare saved evidence. | Check while reading, as a script does. | Saved evidence replays to the same verdict without devices, and a check can be tested without a lab. JSNAPy (snapshot, then check) and SuzieQ (poll, then assert) split the work the same way. |
| Device output is read as JSON only. | Parse CLI text with regular expressions or TextFSM templates. | Text parsers break on column layout, line wrapping and blank cells. JSON keeps field names and types. ANTA reads EOS JSON, and pyATS/Genie and NAPALM prefer structured output where the platform has it. Linux bonding has no JSON source with the partner system per member, so its normalizer reads `/proc/net/bonding`. |
| A neutral model with one folder per platform. `network_toolkit/intent.py` holds the checks; `platforms/<platform>/intent.py` holds collectors and normalizers. | One check per vendor and command. | A check written once applies to every platform that can normalize the fields. NAPALM getters and Genie models put vendor output behind common fields in the same way. |
| Platform-specific checks where no neutral field exists. | Force every property into the neutral model. | RouterOS configuration properties and the Linux active aggregator have no counterpart elsewhere. Keeping them platform-specific avoids fields that mean different things on different platforms. |
| Every result is `pass`, `fail` or `error`, and `error` is never a pass. | Treat missing evidence as a pass or skip it. | A check that could not see the state has not verified it. ANTA (success, failure, error), pyATS (passed, failed, errored) and nornir-salt (PASS, FAIL, ERROR) use the same three outcomes. |
| Items on one device that need the same reading share it. | Read once per item. | Items then see the same moment, as a JSNAPy snapshot or the ANTA per-device cache does, and a run makes fewer reads. |
| The intent file states exact expected values. No operators, tags, skip rules or OpenConfig paths. | Expressions such as `is-gt`, tag filtering, or an OpenConfig model. | The checks compare normalized fields for equality, which covers device-state intent and keeps the file readable. Selection and arithmetic belong to the caller. NUTS uses the same plain expected-value form. |

## Intent file

An intent file is a YAML list. Each item has these keys:

| Key | Required | Meaning |
| --- | --- | --- |
| `device` | Yes | Device name in the Networka inventory. Its `device_type` selects the platform. |
| `check` | Yes | A check name from the tables below. |
| `expected` | Yes | The expected value or fields. |
| `params` | No | The check's parameters, for example `{bridge: bridge}`. |
| `name`, `source` | No | Labels for reports. |

Any other key, an unknown check, params that do not fit the check, a device
that is not in the inventory, or a check its platform does not support is an
error that names the file and the item. Nothing is read from a device until
every item is valid.

## Run, save and replay

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

```bash
nw intent run intent.yaml --save saved
nw intent replay saved
```

`--save` writes three files:

- `intent.yaml`, a copy of the intent file.
- `evidence.json` with the Networka version and, per device, its
  `device_type`, the collection `started` and `finished` times, and the
  readings. Each reading names its `collector` and `args` and holds the
  replies as `command`, `output` and `error`.
- `results.json` with the overall verdict and, per item, its name, device,
  check, expected and observed value, verdict and reason.

```json
{
  "networka_version": "0.4.1",
  "devices": {
    "dc1-core-mlag1": {
      "device_type": "mikrotik_routeros",
      "readings": [
        {
          "collector": "collect_bridge",
          "args": ["bridge"],
          "replies": {
            ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/monitor bridge once as-value]]": {
              "command": ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/monitor bridge once as-value]]",
              "output": "{\"mlag-state\":\"connected\",\"mlag-active-role\":\"primary\"}",
              "error": null
            }
          }
        }
      ],
      "started": "2026-11-26T06:46:27.247089+00:00",
      "finished": "2026-11-26T06:46:27.247435+00:00"
    }
  }
}
```

Run and replay print the same table, shortened here. In this example the
partner of `ether4` does not report the member as synchronized, collecting
and distributing:

```text
Item                        Check        Expected                        Observed                         Verdict
mlag1 is MLAG primary       mlag         {"connected": true, ...}        {"connected": true, ...}         pass
client2 bond member in use  lacp_member  {"actor": {...}, "partner":     {"actor": {...}, "partner":      fail
                                         {"collecting": true, ...}}      {"collecting": false, ...}}
host port has BPDU guard    property     true                            true                             pass
Intent verdict: fail
```

The intent verdict is `fail` when any item fails, `error` when no item fails
but at least one could not be verified, and `pass` otherwise. The exit
status is 0 for pass, 1 for fail and 2 for error, including an unusable
intent file or evidence.

In Python, `run_intent` collects and then evaluates the evidence through
`replay_intent`, so a replay gives the same results:

```python
from network_toolkit import NetworkaClient, intent

items = intent.load_intent("intent.yaml")
with NetworkaClient() as client:
    report = intent.run_intent(client, items, save_dir="saved", source="intent.yaml")
assert intent.replay_directory("saved").results == report.results
```

Extra keyword arguments of `run_intent` go to `NetworkaClient.run`, for
example `interactive_creds`. A single check can also be called directly on
the evidence of one collector, for example
`intent.check_mlag(evidence, "mikrotik_routeros", "bridge", {"connected": True})`.
The normalizers are public for callers that record a value over time, such
as `uptime_ns` for a before-and-after reboot comparison.

## Checks

Neutral checks compare only the fields named in `expected`.

| `check` | `params` | Fields | RouterOS | Linux |
| --- | --- | --- | --- | --- |
| `bridge_port` | `bridge`, `port` | `forwarding`, `role` (`root`, `designated`, `alternate`, `backup`, `disabled`), `edge` | Yes | No |
| `bridge_ports` | `bridge` | Ports of the bridge, as a sorted list | Yes | No |
| `stp_bridge` | `bridge` | `bridge_id`, `root_bridge_id` (`0xPPPP.mac` in lower case), `root_bridge`, `root_port` (`null` on the root), `topology_changes` | Yes | No |
| `stp_mode` | `bridge` | Spanning-tree protocol, `none` when off | Yes | No |
| `mlag` | `bridge` | `connected`, `role` (`primary`, `secondary`), `state` (the platform's own word) | Yes | No |
| `lacp_member` | `bond`, `member` | LACP flags of actor and partner: `activity`, `timeout`, `aggregation`, `synchronization`, `collecting`, `distributing`, `defaulted`, `expired` | Yes | Yes |
| `lacp_partner_system` | `bond`, `member` | LACP system `priority` and `mac` the partner sends | Yes | Yes |
| `host_entry` | `bridge`, `mac` | Port of the bridge host entry, `null` without one | Yes | No |
| `interface_up` | `interface` | Carrier | Yes | No |

`lacp_member` passes when both the actor and the partner side equal
`expected`. Both MLAG peers present one LACP system ID, so
`lacp_partner_system` gives the same value for each member of an MLAG bond
when read on the partner.

| Platform | `check` | `params` | Why it is platform-specific |
| --- | --- | --- | --- |
| RouterOS | `property` | `menu` in slash form, `where`, `name` | Compares one property of a menu entry, for example `pvid`, `edge`, `bpdu-guard`, `loop-protect`, `lacp-strict` or `mlag-priority`. These are RouterOS configuration names. |
| RouterOS | `version` | none | Compares the version without the channel. The expected value comes from a RouterOS image name. |
| Linux | `bond_member` | `bond`, `member` | Compares the bonding driver's `carrier` (MII Status) and `eligible`: in the active aggregator, and both port states synchronized, collecting and distributing. Aggregator selection is a Linux bonding concept. |

## RouterOS commands

Each command runs inside
`:put [:serialize to=json options=json.no-string-conversion [<command>]]`.
A collector joins its few commands with `;` into one read and splits the
output into one reply per command, because each prints one JSON line. Every
collector is a separate read. One read of all state and configuration
commands together exceeded the default 5 s command timeout, so the items of
a device are close in time but not one instant.

| Collector | Command | Checked live |
| --- | --- | --- |
| `collect_bridge`, `collect_bridge_port` | `/interface/bridge/port/print stats as-value` | Yes, 7.20.6, 7.24.5, 7.26beta7 |
| `collect_bridge_port` | `/interface/bridge/port/monitor <id> once as-value` | Yes, 7.20.6, 7.24.5, 7.26beta7 |
| `collect_bridge` | `/interface/bridge/monitor <bridge> once as-value` | Yes, 7.26beta7 |
| `collect_bond` | `/interface/bonding/monitor-slaves bond=<bond> once=yes as-value` | Yes, 7.26beta7 |
| `collect_interface` | `/interface/ethernet/monitor <interface> once as-value` | Yes, 7.26beta7 |
| `collect_host_entry` | `/interface/bridge/host/print as-value where mac-address=<mac>` | Yes, 7.26beta7 |
| `collect_stp_mode` | `/interface/bridge/print as-value where name=<bridge>` | Yes, 7.26beta7 |
| `collect_version` | `/system/resource/print as-value` | Yes, 7.26beta7 |
| `collect_uptime` | `:tonsec [/system/resource/get uptime]` | Yes, 7.26beta7 |
| `collect_print` | `<menu>/print detail as-value` | Not yet; the form without `detail` was read on 7.26beta7 |

What the JSON returns, as seen on 7.26beta7:

- `yes` and `no` states are Booleans, counters are numbers.
- `property` compares values exactly as returned: `edge` is a string such
  as `"yes"` or `"auto"`, `bpdu-guard` a Boolean, `pvid` a number,
  `vlan-ids` an array of strings. A bridge `mtu` of `auto` and a port
  `horizon` of `none` are `0`.
- `print` without `detail` leaves out properties at their default value,
  which is why `collect_print` uses `detail`.
- Durations lose sub-second parts (`mii-interval` 100ms becomes
  `"00:00:00"`), and the bridge monitor's `max-age`, `hello-time` and
  `forward-delay` are whole seconds. No check reads them.
- An inactive bridge port's monitor returns only `.id`, `interface` and
  `status: inactive`. It is normalized as not forwarding.
- A bond member without an LACP partner has no partner fields. Its partner
  flags are normalized as all cleared, and `lacp_partner_system` gives
  `error`.
- The bonding monitor returns one object for one member and an array for
  several.

## Add a platform

The steps use Cumulus Linux as the example. No Cumulus module exists yet;
the sources below are from the NVIDIA guides and
[draft PR #47](https://github.com/narrowin/networka/pull/47) and have not
been checked on a switch.

1. Create `src/network_toolkit/platforms/<device_type>/intent.py`.
2. Add a collector for each concept the platform supports, with the names
   in `intent.CHECKS`, for example `collect_bridge(client, device, bridge)`.
   Read JSON where the platform has it and keep each reply through
   `intent.read`, keyed by its command.
3. Add the normalizers the neutral checks look up: `bridge_port`,
   `bridge_ports`, `stp_bridge`, `stp_mode`, `mlag`, `lacp_member`,
   `host_interface` and `interface_up`. Each returns the neutral fields,
   leaves out a field the platform does not report, and raises `ValueError`
   when the evidence cannot decide. For Cumulus:

   | Neutral fields | Cumulus source | Maps |
   | --- | --- | --- |
   | `bridge_port` `forwarding` | `bridge -j link show dev <port>`, `state` is `forwarding` | Yes |
   | `bridge_port` `role`, `edge` | `mstpctl showportdetail <bridge> <port>`, role and oper edge port; a JSON form is still to be confirmed | Yes |
   | `bridge_ports` | `bridge -j link show`, ports whose `master` is the bridge | Yes |
   | `stp_bridge` | `mstpctl showbridge <bridge>`: bridge ID, designated root, root port, topology change count | Partly: bridge IDs print as `8.000.mac` and need converting to `0xPPPP.mac` |
   | `stp_mode` | `nv show bridge domain <bridge> stp --output json`, mode | Partly: `pvrst` has no RouterOS counterpart |
   | `mlag` `connected`, `role` | `nv show mlag --output json`, peer alive and role | Partly: MLAG is not bridge-scoped on Cumulus, so `bridge` selects nothing |
   | `mlag` `state` | none | No: the state word is each platform's own |
   | `lacp_member`, `lacp_partner_system` | `/proc/net/bonding/<bond>`, as the Linux module reads it | Yes |
   | `host_entry` | `bridge -j fdb show br <bridge>`, `ifname` of the MAC | Yes |
   | `interface_up` | `nv show interface --output json`, `link.oper-status` | Yes |

4. Put the platform's own checks in a `CHECKS` dictionary of `intent.Check`
   entries, for example a Cumulus check of a CLAG setting with no neutral
   field. Use an empty dictionary when there are none.
5. Add the module to `intent.PLATFORMS`. An intent item whose collector or
   normalizer is missing on that platform is an error naming the item.
6. Save replies from a lab device and add a test that replays them, as
   `tests/test_intent.py` does for Linux.

The development setup needs uv 0.13.10, as pinned in `pyproject.toml`. The
[intent examples](examples/intent/README.md) replay archived MLAG lab
evidence.
