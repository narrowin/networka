# Intent verification

Compare how a switch should be operating with what its read-only commands
report. Each check prints the source, command, expected value, observed
value, and verdict.

## Declare the intent

An intent identifies an object, a field, and the value you expect.

| Target | Field being checked | Expected value | Where |
| --- | --- | --- | --- |
| RouterOS bridge port, for example `bridge/access-uplink` | Bridge-port monitor `forwarding` | `true` | Library |
| Cumulus `bond1` | NVUE `link.oper-status` | `up` | [Draft PR #47](#validate-cumulus-in-the-lab) |
| Cumulus `br_default/swp1` | Linux bridge port `state` | `forwarding` | [Draft PR #47](#validate-cumulus-in-the-lab) |

## Check a RouterOS bridge port

`network_toolkit.platforms.mikrotik_routeros.intent` reads and checks the
RouterOS bridge-port forwarding flag. Collection and evaluation are separate,
so saved evidence replays to the same verdict without the device.

```python
import json
from pathlib import Path

from network_toolkit import NetworkaClient
from network_toolkit.platforms.mikrotik_routeros.intent import (
    check_bridge_port_forwarding,
    collect_bridge_port,
)

with NetworkaClient() as client:
    evidence = collect_bridge_port(client, "dc1-core-mlag1", "bridge", "access-uplink")
Path("access-uplink.json").write_text(json.dumps(evidence))

result = check_bridge_port_forwarding(
    evidence, "bridge", "access-uplink", expected=True
)
print(result.expected, result.observed, result.verdict, result.reason)
```

1. `collect_bridge_port` runs the bridge-port statistics command, selects the
   row whose `bridge` and `interface` match, and runs the monitor command for
   that row's `.id`. Each reply is kept as `command`, `output`, and `error`.
   A read failure is recorded in the evidence, not raised. Extra keyword
   arguments go to `NetworkaClient.run`, for example `interactive_creds`.
2. `check_bridge_port_forwarding` selects the port again from the saved
   statistics, requires the monitor reply for the same `.id`, and reads its
   `forwarding` Boolean.
3. Equality is **match**. A differing Boolean is **mismatch**. A read error,
   invalid JSON, a missing or ambiguous port, a reply for another command, or
   a missing field is **unavailable**, and `reason` says why.

For a live RouterOS match and an offline negative control using the same
reply, see the [Medium MikroTik lab replay](examples/intent/README.md#medium-mikrotik-lab-replay).

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
