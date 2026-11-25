# Intent verification

Use the offline intent example to compare how a switch should be operating
with what its read-only commands report. The script prints the source,
command, expected value, observed value, and verdict for each check.

## Declare the intent

An intent identifies an object, a field, and the value you expect. The example
takes the object names as command-line arguments. Its expected values are
declared in Python and shown in the report.

| Example target | Field being checked | Expected value |
| --- | --- | --- |
| RouterOS `bridge/access-uplink` | Bridge-port monitor `forwarding` | `true` |
| Cumulus `bond1` | NVUE `link.oper-status` | `up` |
| Cumulus `br_default/swp1` | Linux bridge port `state` | `forwarding` |

## Evaluate a reply

1. Capture the successful reply from the selected device and command. Save the
   raw JSON locally so the same evidence can be reviewed and replayed.
2. Decode with `json.loads` and select the named object. RouterOS finds the
   bridge and interface in the port statistics, then checks the matching `.id`
   in the monitor reply. Cumulus selects the NVUE interface by name and the
   Linux bridge port by `master` and `ifname`.
3. Compare the observed value with the expected value. Equality is **match**.
   A recognized differing value is **mismatch**. A failed read, invalid JSON,
   absent field, unknown value, or ambiguous object is **unavailable**.
   The Cumulus bridge check maps `forwarding` to `true` and other recognized
   states to `false` before comparing.

For example, this illustrative NVUE reply gives a mismatch for `bond1`.

```json
{"bond1":{"link":{"oper-status":"down"}}}
```

```text
Operational status       expected='up' actual='down' → mismatch
```

Check the verdict lines. The process exit status reports whether the example
ran. For a live RouterOS match and an offline negative control using the same
reply, see the [Medium MikroTik lab replay](examples/intent/README.md#medium-mikrotik-lab-replay).

## Run the archive example

From the Networka checkout, set `MLAG` to the local checkout of
`narrowin/mikrotik-mlag-testsuite`. The archive replay uses commit
`59299681efd9089e6bba5a008cb1e220bb94d19e` and Python 3.11 or later.
[Archive details and additional examples](examples/intent/README.md).

```bash
MLAG=/absolute/path/to/mikrotik-mlag-testsuite
PYTHONPATH="$MLAG/src" uv run --offline --no-project python docs/examples/intent/compare.py "$MLAG"
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
