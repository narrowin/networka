# Experimental operational intent comparison

Run this offline example from the Networka repository root. It reads selected
records from the MLAG lab checkout and uses the lab's existing RouterOS parser.
It also reads a projection of one published Junos interface row embedded in
the script. The example prints the source, command, expected and actual values,
and verdict for each check. The verdicts are in the report, and the process
exit status indicates whether the example ran. [Example script](compare.py).

```bash
MLAG=/path/to/mikrotik-mlag-testsuite
PYTHONPATH="$MLAG/src" uv run --offline --no-project python docs/examples/intent/compare.py "$MLAG"
```

The command uses the parser from source and requires Python 3.11 or later.
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
command result as a string in `output`. The example has no live
Networka-to-device acquisition and qualifies only these archive rows and
the published Junos shape. [Networka run and storage guide][networka-run].

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
