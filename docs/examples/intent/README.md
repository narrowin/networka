# Experimental operational intent comparison

Start with the [intent verification guide](../../intent.md) for the workflow
and the Cumulus lab instructions. This example provides the replay and
supporting evidence.

Run this offline example from the Networka repository root. It reads selected
records from the MLAG lab checkout and uses the lab's existing RouterOS parser.
It also reads a projection of one published Junos interface row embedded in
the script. The example prints the source, command, expected and actual values,
and verdict for each check. The verdicts are in the report, and the process
exit status indicates whether the example ran. [Example script](compare.py).

```bash
MLAG=/path/to/mikrotik-mlag-testsuite
PYTHONPATH="$MLAG/src" uv run --locked python docs/examples/intent/compare.py "$MLAG"
```

The command uses the lab's parser from source and Networka's RouterOS
bridge-port check from the project environment.
Use an MLAG checkout at commit
`59299681efd9089e6bba5a008cb1e220bb94d19e` to reproduce the archive results.
The power-loss case is
`2026-11-24-power-loss / small-stp-off / 01-primary-power-loss`.
The archive's JSONL is the lab's envelope around raw RouterOS command text or
an SSH error. The parser, `summarize_router`, extracts bridge and Ethernet
monitor status from that text.
[Case archive][archive], [Command collector][collector], [RouterOS parser][parser].

The Junos example uses the native JSON shape of
`show interfaces terse | display json` from the published vMX-1 transcript.
The embedded projection preserves the wrapping arrays and `data` fields for
the physical interface `ge-0/0/0`. The printed sample is truncated and
contains one observation for this example. [Published Junos sample, pp. 58–59][juniper].

## Native JSON for spanning-tree intent

To check whether a RouterOS bridge port is forwarding, save the evidence
from `collect_bridge_port` as JSON, as shown in the
[intent guide](../../intent.md#check-a-routeros-bridge-port). It reads these two
read-only replies from the same device in one collection window. The `.id`
in the monitor command comes from the statistics row whose `bridge` and
`interface` match, and only joins the two replies.

```routeros
:put [:serialize to=json options=json.no-string-conversion [/interface/bridge/port/print stats as-value]]
:put [:serialize to=json options=json.no-string-conversion [/interface/bridge/port/monitor *4 once as-value]]
```

Replay the saved evidence with the example. It calls
`check_bridge_port_forwarding` with the expected `true`.
[Example implementation](compare.py) · [RouterOS scripting reference][routeros-scripting].

```bash
PYTHONPATH="$MLAG/src" uv run --locked python docs/examples/intent/compare.py "$MLAG" \
  --routeros-stp-port bridge ether2 ether2-evidence.json
```

In CHR 7.20.6 and 7.24.5 evidence, `ether2` supplied `false` (mismatch),
a forwarding bond supplied `true` (match), and a disabled `ether3` omitted
the field (unavailable). A command error, invalid JSON, ambiguous port, or
wrong monitor ID also makes the check unavailable.

### Medium MikroTik lab replay

On 2026-11-25 the two Medium cores and the access switch ran RouterOS CHR
7.26beta7. This read-only SSH capture used the commands above. Each core's
`access-uplink` resolved to `*1` and the access switch's `uplink` to `*0`.
The check ran on the saved device replies.

On `dc1-core-mlag1`, the port statistics contained this row with unrelated
fields omitted. The `monitor *1 once as-value` reply carried the same `.id`
and the native Boolean shown below.

```json
{".id":"*1","bridge":"bridge","interface":"access-uplink"}
```

```json
{".id":"*1","interface":"access-uplink","forwarding":true,"status":"in-bridge"}
```

| Device | Selected bridge port | Expected forwarding | Observed forwarding | Verdict |
| --- | --- | --- | --- | --- |
| `dc1-core-mlag1` | `access-uplink` (`*1`) | `true` | `true` | Match |
| `dc1-core-mlag2` | `access-uplink` (`*1`) | `true` | `true` | Match |
| `dc1-access-switch1` | `uplink` (`*0`) | `true` | `true` | Match |

As an offline negative control, the comparator expected `false` against
the unchanged core-1 reply and reported a mismatch. A separate native JSON
read with `:put [:serialize to=json options=json.no-string-conversion
[/interface/bridge/print as-value]]` returned `protocol-mode: "none"` on all
three bridges. That differs from the checked-in `rstp` startup profile.
The forwarding verdict describes the bridge-port flag. The live snapshot had
no active STP election. [Medium startup reference][medium-startup].

## Intent verdicts

The shared intent expects physical link status `up`. RouterOS supplies
`ether2` status from `/interface ethernet monitor ether2 once`. Junos supplies
`oper-status` from the selected physical interface row. Its separate
`admin-status` field describes administrative state and plays no part in
the comparison.

| Evidence | Native expected → actual | Translated expected → actual | Verdict |
| --- | --- | --- | --- |
| [RouterOS p2/ether2, before][p2-before] | `link-ok` → `link-ok` | `up` → `up` | Match |
| [RouterOS p2/ether2, during][p2-after] | `link-ok` → `no-link` | `up` → `down` | Mismatch |
| [RouterOS p2/ether2, recovered][p2-recovered] | `link-ok` → `link-ok` | `up` → `up` | Match |
| [RouterOS p1/ether2, during][p1-timeout] | `link-ok` → unavailable | `up` → unavailable | Unavailable. SSH timed out. |
| [Junos vMX-1/ge-0/0/0][juniper] | `up` → `up` | `up` → `up` | Match against the published row |

The bridge checks stay vendor-specific in both paths. Both peers report
`mlag-state=connected` before power loss, with `primary` on p1 and
`secondary` on p2. During power loss, p2 reports `peer port not running`
and omits the active role. Both values are unavailable on p1 after the SSH
timeout. The recovered p2 sample reports `connected` and `secondary`
again. These values come from `/interface bridge monitor bridge once`.

## Baseline differences

The baseline uses one observation fully inside the scored baseline window
for each peer. During power loss, p2's physical link and MLAG state are
`changed` against baseline, while its active role comparison is
`unavailable`. The SSH timeout leaves all three p1 comparisons
`unavailable` until it responds again. Observations fully inside the
scored recovery window match all three baseline facts on both peers.
The Junos excerpt supplies a single fact. The selected checks leave extra
interfaces outside their scope. A missing field or row provides insufficient
evidence to assert that an interface is absent. [Power-loss timeline][power-events],
[p1 baseline][p1-before], [p1 recovery][p1-recovered],
[p2 baseline][p2-before], [p2 recovery][p2-recovered].

## Bond eligibility and spanning tree

In the Small lab MSTP bond-member-loss case, the captured configuration
binds `client1` to `ether3` and `client2` to `ether4` on each peer.
The RouterOS LACP monitor reports synchronized, collecting and distributing
(`SCD`) flags on both actor and partner for all four configured members in
the first samples. In p1's fault-window sample, `client1/ether3` has
`no-link` and loses LACP eligibility. `client2/ether4` still matches.
This verifies the selected links' LACP eligibility and detects a loss of
redundancy on one leg. Client-to-client reachability is checked separately.
[p1 configuration][bond-config-p1], [p2 configuration][bond-config-p2],
[p1 before][bond-p1-before], [p2 before][bond-p2-before],
[p1 during][bond-p1-during], [collector commands][legacy-collector].

In the same case, p1 reports CIST (Common and Internal Spanning Tree) root
ID `0x1000.52:54:00:d7:0b:01` before and during the member loss. Before
loss, `client1` is a `designated-port` with `forwarding=yes`. During
loss, the multi-port command prints blanks in the `client1` role and
forwarding columns. The existing whitespace parser can shift another
port's values into those blanks. The example checks column counts and marks
both client1 checks unavailable for that sample. The CIST result covers
the selected bridge and port. [p1 during][bond-p1-during],
[port parser][port-parser].

## Reachability between the selected clients

The Small lab MSTP direct-baseline report scores ICMP requests and replies
at the two bonded VLAN 110 endpoints. Direction `101` is Client A to B
and direction `201` is Client B to A in this case. Both match the expectation
that all baseline probes were delivered. Flow IDs belong to their lab case
and topology. The legacy bond-member-loss case reuses `101` and `201` for
client1 and mobile, so neither ID identifies a direction across cases.
[Direct-baseline report][probe-report], [direct flow mapping][direct-flows],
[root flow definitions][root-flows], [legacy flow definitions][legacy-flows].

The check requires a row for each selected direction and verifies that its
positive send count is accounted for by `baseline_good` and
`baseline_missed`, with an empty `capture_mismatches` list. Recorded
misses produce a mismatch with valid evidence. Missing directions,
unaccounted or absent sends, and unverified endpoint agreement produce
unavailable. The inputs here are lab-scored packet capture results from
the named baseline, and the conclusion covers its two probed directions.
[Lab scoring code][probe-score].

An interrupted secondary-reboot report has no missed probes in the
recorded samples for either direction. The report records an interruption
and marks both withdrawal and restoration as errors. The full reboot
window verdict is unavailable for both directions. [Recorded interruption][probe-interrupted],
[incomplete phases][probe-interrupted-phases].

## Where the two approaches differ

Both approaches need command-specific extraction. The native check also
requires the operator to know each command's field and expected value. The
translated check keeps that decision next to the extractor so one expectation
can be used by both platforms. This example maps two RouterOS values, passes
through known Junos values, and leaves the MLAG checks native.

Networka can supply the acquisition side from `RunResult`. Use
`command_results` for each device's command, output and error, or
`sequence_results` for its command-keyed outputs and device error. Route
the raw string to the decoder for its platform and exact command and carry
any failure into the verdict. Networka's stored JSON also carries the
command result as a string in `output`. The runnable `compare.py` example
uses the archive rows and the published Junos shape offline.
[Networka run and storage guide][networka-run].

## Medium lab qualification on 2026-11-25

A one-off SDK capture with the published Networka v0.3.0 wheel and native
Scrapli on Python 3.15.2 supplied live RouterOS output for the same selected
operational checks. The two core peers and access switch all ran RouterOS CHR
7.26beta7. The check used read-only RouterOS commands and VLAN 110 endpoint
probes. The results describe one live snapshot. No faults were injected and no
configuration was changed.

- **Ethernet and MLAG.** Each of the three devices reported `link-ok` on
  `ether2`, `ether3` and `ether4`. The core peers both reported
  `mlag-state=connected`, with `primary` on the first peer and `secondary`
  on the second.
- **LACP.** All six selected members were eligible. The actor and partner
  both reported `SCD` on `access-uplink/ether3` and `client2/ether4` on each
  core peer, and on `uplink/ether2` and `uplink/ether3` on the access switch.
- **Reachability.** All three VLAN 110 pings succeeded in each direction
  between the two selected endpoints.
- **Spanning tree.** The running bridges reported `protocol-mode=none`,
  which differs from the startup reference's RSTP mode. The selected ports
  reported `forwarding=yes`. Active spanning-tree root and port-role checks
  were inapplicable with STP disabled. The reported root ID
  `0x8000.00:00:00:00:00:00` is a placeholder. [Medium startup reference][medium-startup].

For core 1, the intent declares the two expected RouterOS bridge fields
directly. This fragment uses an initialized `NetworkaClient` as `client`
and the example's `summarize_router` and `show_intent` helpers.

```python
intent = {
    "device": "dc1-core-mlag1",
    "command": "/interface bridge monitor bridge once",
    "expected": {"mlag-state": "connected", "mlag-active-role": "primary"},
}

result = client.run(intent["device"], intent["command"])
reply = next(
    (
        row
        for row in result.command_results
        if (row.device, row.command) == (intent["device"], intent["command"])
    ),
    None,
)
facts = {}
if reply is not None and reply.error is None and reply.output is not None:
    facts = summarize_router(reply.output)["bridge"]

for field, expected in intent["expected"].items():
    show_intent(field, expected, facts.get(field))
```

Both fields matched in the live sample. A different reported value produces
`mismatch`. A failed or missing reply or an omitted field produces
`unavailable` for the affected checks.

[archive]: https://github.com/narrowin/mikrotik-mlag-testsuite/tree/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss
[collector]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/external_run.py#L215-L218
[parser]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/root_evidence.py#L84-L95
[power-events]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss/events.jsonl#L2-L15
[p2-before]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss/state-p2.jsonl#L3
[p2-after]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss/state-p2.jsonl#L17
[p2-recovered]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss/state-p2.jsonl#L171
[p1-before]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss/state-p1.jsonl#L3
[p1-recovered]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss/state-p1.jsonl#L68
[p1-timeout]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-power-loss/small-stp-off/01-primary-power-loss/state-p1.jsonl#L16
[bond-config-p1]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-small-search/mstp-default-l2/01-bond-member-loss/config-p1.txt#L54-L66
[bond-config-p2]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-small-search/mstp-default-l2/01-bond-member-loss/config-p2.txt#L54-L66
[bond-p1-before]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-small-search/mstp-default-l2/01-bond-member-loss/state-p1.jsonl#L1
[bond-p2-before]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-small-search/mstp-default-l2/01-bond-member-loss/state-p2.jsonl#L1
[bond-p1-during]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-small-search/mstp-default-l2/01-bond-member-loss/state-p1.jsonl#L20
[legacy-collector]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/run.py#L43-L52
[port-parser]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/root_state.py#L16-L35
[probe-report]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-forwarding-checks/small-mstp-reboots/01-baseline/result.json#L575-L605
[probe-interrupted]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-forwarding-checks/small-mstp-reboots/01-secondary-reboot/result.json#L4-L9
[probe-interrupted-phases]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/results/2026-11-24-forwarding-checks/small-mstp-reboots/01-secondary-reboot/result.json#L1076-L1105
[direct-flows]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/direct_topology.py#L20-L23
[root-flows]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/root_topology.py#L42-L47
[legacy-flows]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/legacy.py#L18-L28
[probe-score]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/src/mlag_lab/measure.py#L23-L49
[juniper]: https://www.juniper.net/documentation/en_US/day-one-books/DO_Automating_SALT.pdf#page=58
[networka-run]: ../../running-commands.md
[routeros-scripting]: https://manual.mikrotik.com/docs/developer-guides/scripting/
[medium-startup]: https://github.com/narrowin/mikrotik-mlag-testsuite/blob/59299681efd9089e6bba5a008cb1e220bb94d19e/labs/medium/medium.rsc#L2-L16
