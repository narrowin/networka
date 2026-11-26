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
| Device output is read as JSON only. | Parse CLI text with regular expressions or TextFSM templates. | Text parsers break on column layout, line wrapping and blank cells. JSON keeps field names and types. ANTA reads EOS JSON, and pyATS/Genie and NAPALM prefer structured output where the platform has it. Two sources have no JSON form and are read as text: Linux bonding (`/proc/net/bonding`, which alone gives the partner system per member) and the Linux `ping` summary line. |
| A neutral model with one folder per platform. `network_toolkit/intent.py` holds the checks; `platforms/<platform>/intent.py` holds collectors and normalizers. | One check per vendor and command. | A check written once applies to every platform that can normalize the fields. NAPALM getters and Genie models put vendor output behind common fields in the same way. |
| Platform-specific checks where no neutral field exists. | Force every property into the neutral model. | RouterOS configuration properties and the Linux active aggregator have no counterpart elsewhere. Keeping them platform-specific avoids fields that mean different things on different platforms. |
| Every result is `pass`, `fail` or `error`, and `error` is never a pass. | Treat missing evidence as a pass or skip it. | A check that could not see the state has not verified it. ANTA (success, failure, error), pyATS (passed, failed, errored) and nornir-salt (PASS, FAIL, ERROR) use the same three outcomes. |
| Absence needs positive proof, and every reply must identify its object. | Read an empty reply as "not there", and trust a reply to be about what was asked. | Before reading a value, a normalizer checks that the reply names the requested object by its key: the bridge print row `name` and the bridge monitor `.id` that matches it, the Ethernet monitor `name`, the bond row `port`, the host row `mac-address` and `bridge`, the port monitor `interface`. It reports `null` or an empty list only from such a reply that shows the object exists, for example a bridge print that contains the bridge. A missing or mismatched key, `{}`, or a failed or missing reply is `error`. |
| Items on one device share a reading when they use the same collector with identical params. | Read once per item. | Those items then see the same moment, as a JSNAPy snapshot or the ANTA per-device cache does. Items whose params differ read separately, even on the same command: two `property` items on the same menu read it twice. |
| The overall verdict is fail-first: any `fail` makes the run `fail` (exit 1), even when other items are `error`. | Error-first, where one unverifiable item hides a confirmed failure. | A confirmed wrong state is the more urgent finding; the `error` items stay listed with their reasons. ANTA and pyATS report a failed run the same way. |
| The intent file states exact expected values. No operators, tags, skip rules or OpenConfig paths. | Expressions such as `is-gt`, tag filtering, or an OpenConfig model. | The checks compare normalized fields for equality, which covers device-state intent and keeps the file readable. Selection and arithmetic belong to the caller. NUTS uses the same plain expected-value form. |

Evidence trust: replay trusts that `evidence.json` was written by Networka
for the devices it names. Replies are identified by device and exact
command; RouterOS `monitor-slaves` does not echo the bond name, so the
command is the bond's identity. Hand-edited evidence, or replies swapped
between devices, is out of scope, as it is for JSNAPy and Genie snapshots.
Duplicate keys and NaN or Infinity in the evidence or a reply, and duplicate
keys in an intent file, are rejected.

## Intent file

An intent file is a YAML list. Each item has these keys:

| Key | Required | Meaning |
| --- | --- | --- |
| `device` | Yes | Device name in the Networka inventory. Its `device_type` selects the platform. |
| `check` | Yes | A check name from the tables below. |
| `expected` | Yes | The expected value or fields. |
| `params` | No | The check's parameters, for example `{bridge: bridge}`. |
| `name`, `source` | No | Labels for reports. |

Every item goes through one validation, whether it comes from a file or is
built in Python, and an error names the file or `where` label and the item:
an unknown key or check, missing or extra params, a param value that is not
a plain name (`bridge`, `bond`, `member`, `port`, `interface`: letters,
digits, `_`, `.`, `/` and `-`, so `ether1/1` works), a MAC address, a menu
path such as `/interface/bridge/port`, or a `where` mapping of property
names to scalars, and an `expected` that is not JSON-native (strings,
integers, Booleans, null, lists and mappings; YAML dates and floats are
rejected) or does not fit the check's shape and types (`true` is not `1`).
A MAC address must be quoted, or YAML may read it as a number. Before any device is read, each device is resolved in the inventory
the same way `nw run` resolves it, and its `device_type` must support the
check.

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
- name: gateway answers every probe
  device: dc1-core-mlag1
  check: ping
  params: {dest: 192.0.2.1, count: 3}
  expected: {reachable: true}
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

- `intent.yaml`, the validated items, written before any device is read.
  Replay uses exactly these items.
- `evidence.json` with the Networka version and, per device, its
  `device_type`, the collection `started` and `finished` times, and the
  readings. Each reading names its `collector` and `args` and holds the
  replies as `command`, `output` and `error`.
- `results.json` with the overall verdict and, per item, its name, source,
  device, check, expected and observed value, verdict and reason.

The evidence of the first item, as saved; with that item it replays to
`pass`:

```json
{
  "networka_version": "0.4.1",
  "devices": {
    "dc1-core-mlag1": {
      "device_type": "mikrotik_routeros",
      "readings": [
        {
          "collector": "collect_bridge",
          "args": [
            "bridge"
          ],
          "replies": {
            ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/print as-value where name=\"bridge\"]]": {
              "command": ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/print as-value where name=\"bridge\"]]",
              "output": "[{\".id\":\"*A\",\"name\":\"bridge\",\"protocol-mode\":\"none\"}]",
              "error": null
            },
            ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/monitor \"bridge\" once as-value]]": {
              "command": ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/monitor \"bridge\" once as-value]]",
              "output": "{\".id\":\"*A\",\"mlag-state\":\"connected\",\"mlag-active-role\":\"primary\"}",
              "error": null
            },
            "stats": {
              "command": ":put [:serialize to=json options=json.no-string-conversion [/interface/bridge/port/print stats as-value]]",
              "output": "[{\".id\":\"*1\",\"bridge\":\"bridge\",\"interface\":\"ether4\"}]",
              "error": null
            }
          }
        }
      ],
      "started": "2026-11-26T07:28:15.246775+00:00",
      "finished": "2026-11-26T07:28:15.247179+00:00"
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
gateway answers every probe ping         {"reachable": true}             {"reachable": true}              pass
host port has BPDU guard    property     true                            true                             pass
Intent verdict: fail
```

The intent verdict is `fail` when any item fails, `error` when no item fails
but at least one could not be verified, and `pass` otherwise. The exit
status is 0 for pass, 1 for fail and 2 for error, including an unusable
intent file or evidence; the command then prints one `error:` line and no
traceback. Values compare in value and type, also inside mappings and
lists. A reply succeeded only when its `error` is exactly `null`, and a
reading only when it has no `error` key; any other value, including `""`
or `false`, is an error. Malformed evidence, such as a device without a
list of readings, a reading or a used reply with an error, and any failure
inside a check give that item `error`, in a run and in a replay alike.
When a read finds that a device does not accept a connection, its remaining
readings in that run are not attempted and carry the same error.

In Python, `run_intent` collects and then evaluates the evidence through
`replay_intent`, so a replay gives the same results:

```python
from network_toolkit import NetworkaClient, intent

items = intent.load_intent("intent.yaml")
with NetworkaClient() as client:
    report = intent.run_intent(client, items, save_dir="saved")
assert intent.replay_directory("saved").results == report.results
```

Extra keyword arguments of `run_intent` go to `NetworkaClient.run`, for
example `interactive_creds`. A single check can also be called directly on
the evidence of one collector, for example
`intent.check_mlag(evidence, "mikrotik_routeros", "bridge", {"connected": True})`.
The normalizers are public for callers that record a value over time, such
as `uptime_ns` for a before-and-after reboot comparison.

Runner contract: collectors need only an object with
`run(device, command, **options)` that returns Networka's result shape, an
object whose `command_results` hold `device`, `output` and `error` per
device; `run_intent` also reads `client.config` to resolve devices. In
production that is `NetworkaClient` over SSH. A lab can pass its own runner
with the same shape, for example one that runs the command in a container
namespace, and the same check works with both transports. Networka itself
knows nothing about namespaces.

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
| `bond_members` | `bond` | Member ports of the bond, as a sorted list (like ANTA's VerifyPortChannels); every member row must name its port | Yes | Yes |
| `host_entry` | `bridge`, `mac` | Port of the bridge host entry, `null` without one; an entry for the MAC on another bridge is `error` | Yes | No |
| `interface_up` | `interface` | Carrier | Yes | No |
| `ping` | `dest`, `count` (1 to 100), optional `interface` and `vrf` (on Linux one of the two) | `sent`, `received`, `reachable` (every probe answered) | Yes | Yes |

`ping` is the production counterpart of the MLAG lab's reachability
probes. The lab's 100 ms outage probes with per-port captures stay in that
lab. A reply that says the destination is unreachable, such as Linux
`ping: connect: Network is unreachable` or "Destination Host Unreachable",
or a RouterOS probe row with a `status` such as `timeout` or
`no route to host`, counts as a lost probe and fails; only an unparseable reply or one for another
address is `error`, as in ANTA's VerifyReachability. A tolerance for
partial loss is out of scope, as there are no
operators: expect `reachable: true`, or the exact `received` count. On
Linux the `count` probes must finish within the device's `command_timeout`.

`lacp_member` passes when both the actor and the partner side equal
`expected`; a member without an LACP partner gives `error` with reason
"no LACP partner". The partner MAC is compared in lower case. Both MLAG peers present one LACP system ID, so
`lacp_partner_system` gives the same value for each member of an MLAG bond
when read on the partner.

| Platform | `check` | `params` | Why it is platform-specific |
| --- | --- | --- | --- |
| RouterOS | `property` | `menu` in slash form, `where`, `name` | Compares one property of a menu entry; an absent property is `error`, not `null`. For example `pvid`, `edge`, `bpdu-guard`, `loop-protect`, `lacp-strict` or `mlag-priority`. These are RouterOS configuration names. |
| RouterOS | `version` | none | Compares the version without the channel. The expected value comes from a RouterOS image name. |
| Linux | `bond_member` | `bond`, `member` | Compares the bonding driver's `carrier` (MII Status) and `eligible`: in the active aggregator, and both port states synchronized, collecting and distributing. Aggregator selection is a Linux bonding concept. |

## RouterOS commands

Each command runs inside
`:put [:serialize to=json options=json.no-string-conversion [<command>]]`.
Names are quoted in the command, and only validated names, MAC addresses and
menu paths reach it. `collect_bridge` reads the bridge print and the bridge
monitor in one read and the port statistics in another, so a failed
statistics read leaves MLAG and STP checks usable; `collect_host_entry`
reads the host print and the bridge print in one read; and
`collect_bridge_port` reads the statistics and then the monitor of the
selected port. `collect` can join several commands with `;` into one read
and splits the output into one reply per command, because each prints one
JSON line. One read of all state and configuration commands together
exceeded the default 5 s command timeout, so the items of a device are close
in time but not one instant.

| Collector | Command | Checked live |
| --- | --- | --- |
| `collect_bridge`, `collect_bridge_port` | `/interface/bridge/port/print stats as-value` | Yes, 7.20.6, 7.24.5, 7.26beta7 |
| `collect_bridge_port` | `/interface/bridge/port/monitor <id> once as-value` | Yes, 7.20.6, 7.24.5, 7.26beta7 |
| `collect_bridge` | `/interface/bridge/print as-value where name="<bridge>"` and `/interface/bridge/monitor "<bridge>" once as-value`, in one read | Yes, 7.26beta7 |
| `collect_bond` | `/interface/bonding/monitor-slaves bond=<bond> once=yes as-value` | Yes, 7.26beta7 |
| `collect_interface` | `/interface/ethernet/monitor <interface> once as-value` | Yes, 7.26beta7 |
| `collect_host_entry` | `/interface/bridge/host/print as-value where mac-address=<mac>` and the bridge print, in one read | Yes, 7.26beta7 |
| `collect_stp_mode` | `/interface/bridge/print as-value where name=<bridge>` | Yes, 7.26beta7 |
| `collect_version` | `/system/resource/print as-value` | Yes, 7.26beta7 |
| `collect_uptime` | `:tonsec [/system/resource/get uptime]` | Yes, 7.26beta7 |
| `collect_ping` | `/ping address=<dest> count=<count> [interface="<interface>"] [vrf="<vrf>"] as-value` | Yes, 7.26beta7, without `vrf` |
| `collect_print` (params `menu`, `where`, `name`) | `<menu>/print detail as-value` | Yes, 7.26beta7 |

RouterOS returns one row per probe and no totals row: an answered probe
has `host`, `seq`, `size`, `time` and `ttl`; a lost one has a `status`
(`timeout` with `host`, `no route to host` without it). The normalizer needs
exactly `count` rows with `seq` 0 to `count - 1`, any `host` equal to
`dest`, and counts rows with `ttl` and `time` and no `status` as received.

All of these, including the quoted names such as `monitor "bridge" once`
and the joined host print and bridge print, were read on RouterOS CHR
7.26beta7. The Linux bonding normalizer has been checked only against saved
`/proc/net/bonding` text from lab hosts, not through a Networka `linux`
device.

What the JSON returns, as seen on 7.26beta7:

- `yes` and `no` states are Booleans, counters are numbers.
- `property` compares values exactly as returned: `edge` is a string such
  as `"yes"` or `"auto"`, `bpdu-guard` a Boolean, `pvid` a number,
  `vlan-ids` an array of strings. A bridge `mtu` of `auto` and a port
  `horizon` of `none` are `0`.
- `print` without `detail` leaves out properties at their default value,
  for example the bridge port's `learn` and `priority`, the bridge VLAN's
  `tagged` and `untagged`, and the Ethernet `loop-protect`. That is why
  `collect_print` uses `detail`.
- Durations lose sub-second parts (`mii-interval` 100ms becomes
  `"00:00:00"`), and the bridge monitor's `max-age`, `hello-time` and
  `forward-delay` are whole seconds. No check reads them.
- An inactive bridge port's monitor returns only `.id`, `interface` and
  `status: inactive`. It is normalized as not forwarding.
- A bond member with an LACP partner has `partner: true`. Without one, as
  seen once while a member came back, the row has no `partner`,
  `partner-flags`, `partner-key`, `partner-sys-id` or `partner-sys-priority`,
  for example `{"active": true, "flags": "ATG---FE", "key": 15,
  "port": "ether3"}`. Checks on the partner side then give `error`.
- The bonding monitor returns one object for one member and an array for
  several.

## Add a platform

This section is written for adding Cumulus Linux; no Cumulus module exists
yet. Read `src/network_toolkit/platforms/linux/intent.py` as the smallest
complete platform module: collectors, normalizers, one platform-specific
check, `PARAM_RULES` and the `claim` call. The Cumulus sources below come
from the NVIDIA guides and
[draft PR #47](https://github.com/narrowin/networka/pull/47) and have not
been checked on a switch.

### Dispatch and registry

Intent checks find a platform only through `intent.PLATFORMS`, which maps a
`device_type` to its module, for example
`"cumulus_linux": "network_toolkit.platforms.cumulus_linux.intent"`.

The entry in `src/network_toolkit/platforms/registry.py` is separate. It
feeds `nw platforms`, the generated platform docs, the vendor-operations
factory and the device types accepted for IP targets, not intent dispatch.
Add `cumulus_linux` there with `status=PlatformStatus.EXPERIMENTAL`,
`has_operations_class=False` and `has_builtin_sequences=False`, like the
`linux` entry. Two existing tests then change:
`tests/test_platforms_cli.py` uses `cumulus_linux` as an example of an
unregistered definition, and `tests/test_intent.py`
(`test_platform_lookup_names_supported_platforms`) lists the supported
intent platforms.

### Reuse the Linux module

Cumulus bonds use the Linux bonding driver and Cumulus runs iputils, so the
Cumulus module imports and re-exports the Linux pieces:

```python
from network_toolkit.platforms.linux.intent import (
    PARAM_RULES,
    bond_members,
    collect_bond,
    collect_ping,
    lacp_member,
    ping,
)
```

`PARAM_RULES` maps a check name to a function that receives the item's
params and raises `ValueError` for a combination the platform cannot run;
`intent._resolve` calls it before any device is read. The Linux rule
rejects `interface` together with `vrf` for `ping`.

The Linux LACP checks (`lacp_member`, `lacp_partner_system`,
`bond_member`) need the device login to read `/proc/net/bonding/<bond>` as
root (CAP_NET_ADMIN): without it the file has no "Active Aggregator Info"
or "details actor/partner lacp pdu" blocks, and the checks give `error`
with reason "LACP details missing from /proc/net/bonding/<bond>; read it as
root (CAP_NET_ADMIN)". `bond_members` needs no root.

On Linux, Networka runs a command in the login shell and does not see its
exit status: stderr and a non-zero exit arrive in the reply `output` with
`error` null, as `ping: connect: Network is unreachable` with exit status 2
did in a live read (see `send_command` in
`transport/scrapli_sync.py`). `error` is set only when Networka itself
fails, for example on a connection or timeout failure, or when the
platform's Scrapli definition marks the output as failed. Normalizers must therefore
recognise failure text in the output.

### Collectors

```python
from network_toolkit import intent
from network_toolkit.intent import Reply


def collect_bridge(client, device, bridge, **run_options) -> dict[str, Reply]:
    command = f"bridge -j link show master {intent.name(bridge, 'bridge')}"
    return {command: intent.read(client, device, command, run_options)}
```

The contract is `(client, device, *collect_args, **run_options) ->
dict[str, Reply]`. A collector receives every param of its check, in the
order the check lists them (optional ones may be left off), and ignores
those it does not need. Validate each param with `intent.name`,
`intent.mac` or `intent.address` before it reaches a command. Read through
`intent.read(client, device, command, run_options)`, passing
`run_options` on so that options such as `interactive_creds` reach
`NetworkaClient.run`; `intent.read` records a read failure in the reply
instead of raising. Return the replies keyed by their command. Read JSON
where the platform has it, with `intent.load_json`.

| Collector and args | Normalizers it feeds |
| --- | --- |
| `collect_bridge(bridge)` | `stp_bridge`, `mlag`, `bridge_ports` |
| `collect_bridge_port(bridge, port)` | `bridge_port` |
| `collect_stp_mode(bridge)` | `stp_mode` |
| `collect_bond(bond, member)` | `lacp_member`, `bond_members` (without `member`) |
| `collect_host_entry(bridge, mac)` | `host_entry` |
| `collect_interface(interface)` | `interface_up` |
| `collect_ping(dest, count, interface, vrf)` | `ping` |

### Normalizers

A normalizer takes the collector's evidence and the params and returns the
neutral fields. It raises `ValueError` with a short reason when the
evidence cannot decide, which becomes the item's `error`, and leaves out a
field the platform does not report, so a check on that field gives
`error`, never a pass. Read replies with `intent.reply_output(evidence,
command)`, which raises unless the reply's `error` is exactly null.

Identity rule: before reading a value, check that the reply names the
requested object by its key field. For a global object with no name, such
as Cumulus MLAG, require a field only that object has, for example
`local-role` in `nv show mlag`. A normalizer that can return `None` or an
empty list must first show from a successful reply that the object exists.

| Normalizer | Returns |
| --- | --- |
| `bridge_port(evidence, bridge, port)` | `{"forwarding": bool, "role": str, "edge": bool}`, role as `root`, `designated`, `alternate`, `backup` or `disabled` |
| `bridge_ports(evidence, bridge)` | `["swp1", "swp2"]` |
| `stp_bridge(evidence, bridge)` | `{"bridge_id": "0x8000.mac", "root_bridge_id": ..., "root_bridge": bool, "root_port": str or None, "topology_changes": int}` |
| `stp_mode(evidence, bridge)` | `"rstp"`, `"mstp"`, `"none"` |
| `mlag(evidence, bridge)` | `{"connected": bool, "role": "primary" or "secondary", "state": str}` |
| `bond_members(evidence, bond)` | `["swp1", "swp2"]`; a successful bond read proves the bond exists |
| `lacp_member(evidence, bond, member)` | `{"actor": {flag: bool}, "partner": {flag: bool}, "partner_system": {"priority": int, "mac": lower-case str}}`, with `partner` and `partner_system` left out when there is no partner |
| `host_entry(evidence, bridge, mac)` | The port name, or `None` when the bridge has no entry |
| `interface_up(evidence, interface)` | `bool` |
| `ping(evidence, dest, count, interface, vrf)` | `{"sent": int, "received": int, "reachable": bool}`; the reply must name `dest` and account for `count` probes |

For Cumulus:

| Neutral fields | Cumulus source | Maps |
| --- | --- | --- |
| `bridge_port` `forwarding` | `bridge -j link show dev <port>`, `state` is `forwarding` | Yes |
| `bridge_port` `role`, `edge` | `mstpctl showportdetail <bridge> <port>`, role and oper edge port; a JSON form is still to be confirmed | Yes |
| `bridge_ports` | `bridge -j link show`, ports whose `master` is the bridge | Yes, with an existence read of the bridge |
| `stp_bridge` | `mstpctl showbridge <bridge>`: bridge ID, designated root, root port, topology change count | Partly: bridge IDs print as `8.000.mac` and need converting to `0xPPPP.mac` |
| `stp_mode` | `nv show bridge domain <bridge> stp --output json`, mode | Partly: `pvrst` has no RouterOS counterpart |
| `mlag` `connected`, `role` | `nv show mlag --output json`, peer alive and role | Partly: MLAG is not bridge-scoped on Cumulus, so `bridge` selects nothing; identify the reply by `local-role` |
| `mlag` `state` | none | No: the state word is each platform's own |
| `lacp_member`, `lacp_partner_system`, `bond_members` | `/proc/net/bonding/<bond>`, the Linux normalizers (root for LACP) | Yes |
| `host_entry` | `bridge -j fdb show br <bridge>`, `ifname` of the MAC | Yes, with an existence read of the bridge |
| `interface_up` | `nv show interface --output json`, `link.oper-status` | Yes |
| `ping` | `ping -n -c <count> -W 1 [-I <interface or vrf>] <dest>`, the Linux collector | Yes |

The member and FDB queries return no rows both for an empty bridge and for
a bridge that does not exist, so those collectors also read the bridge
itself, for example `ip -j link show dev <bridge>`, and the normalizers find
it there before returning `[]` or `None`. Each normalizer also checks the
reply's key fields, `ifname` and `master` for ports and `mac` for FDB rows.

### Platform-specific checks

A check with no neutral field, such as a CLAG setting, goes in the
module's `CHECKS` dictionary. Each entry is

```python
intent.Check(params, collector, evaluate, normalizer=None, expected=..., optional=())
```

- `params`: the required param names, each registered in `intent.PARAMS`
  with its validator (add new ones such as `peer` there).
- `collector`: the name of the module's collector function.
- `evaluate(evidence, device_type, params, expected) -> IntentResult`,
  usually built with `intent.compare(expected, observe)`.
- `normalizer`: `None` for a platform check.
- `expected`: the shape `expected` must have: a tuple of types, a mapping
  of field to types, or `[types]` for a list.
- `optional`: param names that may be left out.

The `bond_member` entry at the end of `platforms/linux/intent.py` is a
complete example. End the module with `intent.claim("<device_type>",
CHECKS)`. Check names share one namespace across platforms: a name may
appear on several platforms only with the same params, optional params and
expected shape, never as a neutral check name, and `claim` fails at import
otherwise. A Cumulus module that re-exports the Linux `bond_member` check
keeps the same contract.

### Checklist

1. Add `cumulus_linux` to `intent.PLATFORMS`, and register it in
   `platforms/registry.py` as experimental; update the two tests named
   above.
2. Create `src/network_toolkit/platforms/cumulus_linux/intent.py` with the
   collectors and normalizers, importing the Linux bonding and ping ones.
3. Add `CHECKS` (empty when there are none), `PARAM_RULES` if needed, and
   `intent.claim("cumulus_linux", CHECKS)`.
4. Read each collector's commands once on a lab switch, as root for the
   LACP checks, save the replies, and add a test that feeds them to the
   checks, as `tests/test_platforms_mikrotik.py` does with RouterOS replies.
   Include a down port and a bond member without a partner.
5. Run an intent file against the lab with `nw intent run FILE --save DIR`
   and check that `nw intent replay DIR` prints the same results.

The development setup needs uv 0.13.10, as pinned in `pyproject.toml`. The
[intent examples](examples/intent/README.md) replay archived MLAG lab
evidence.
