# Lab tests

`nw test run` checks a containerlab lab before, during, and after a sequence of typed actions. It measures IPv4 ping streams and checks switch logs against the test’s log rules. `nw test replay` judges the saved evidence again without the lab.

## Run and replay

Start the lab using its own startup instructions. Run `nw test run` as root on the lab machine, the Linux machine that runs the lab's containers. The lab machine needs `docker`, `ip`, `nsenter`, `tcpdump`, `tshark`, and `ping` from iputils for explicit ICMP identifiers. Impairments and other traffic faults also need `tc` from iproute2 in root’s `PATH`, commonly under `/usr/sbin`. Pass the directory containing the generated `topology-data.json` to `--lab`. All nodes must be running, and the Networka inventory must supply SSH access for state checks, switch recovery, and log markers. An inventory device named after a lab node can omit its `host` field to use the node's management address.

Follow the [Small lab README](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/tests/small/README.md) to start its qualified native CHR lab. With an installed `nw` available to `sudo`, run these commands from the Small lab repository root. For a reboot run, change the first line to `test_name=switch-reboot`. The README also shows how to run the same tests with `uv` from a Networka checkout.

```sh
test_name=bond-member-loss
out=$(mktemp -d)
sudo nw test run "tests/small/$test_name.yaml" \
  --lab tests/small/clab-small-mlag --config tests/small/devices.yml --save "$out"
sudo nw test replay "$out/$test_name"
```

Each input test gets a directory named after its filename without the extension under `--save`. An existing nonempty evidence directory is refused. Pass multiple test files to run them in order. Use `--interactive-auth` to prompt for SSH credentials. Replay needs `tshark` and permission to read the evidence and write the report. [CLI reference](reference/cli.md#nw-test) · [Measured Small lab runs](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/docs/walkthrough-networka-tests.md)

## Files that define a test

A lab file holds its stream directions, state checks and optional switch log. A point is a containerlab node and its interface, written `node:interface`.

| Lab field | Meaning |
| --- | --- |
| `streams` | Each entry gives a unique `name`, a `from` point and a `to` point. Pings target the destination interface's IPv4 address. A `to` written as an IPv4 address, such as a VRRP address on a router, is the fixed ping target and has no capture point. File order assigns the ICMP identifiers. |
| `state` | Each entry is a state check with a `name`, optional `source` and device `checks`. [Intent check format](intent.md) |
| `switch_log` | The file the collector writes, relative to the deployed lab directory. Each line starts with an RFC 3339 receive timestamp and the switch name, followed by the message. Required for log rules. |

A test file gives its `name`, `purpose`, `lab` file path relative to the test and ordered `steps`. It may include a `source` and whole-test `log` rules.

| Step field | Meaning |
| --- | --- |
| `name`, `expected` | Step title and expected behaviour. |
| `cable`, `state` | For a cable change, supply one point and its required state, `down` or `up`. |
| `action` | One of the typed actions below. |
| `recovery_deadline_s` | The recovery deadline: a positive number of seconds for every state check to pass again after a reboot or the end of a power loss. Optional when clearing a traffic fault. |
| `hold_s` | The hold: seconds to keep measuring after the action and, when the action needs them, after the state checks pass again. |
| `check_state` | Optional state checks, each with a `name` and device checks in the lab file’s `state` format. Read after the hold and judged again on replay. |
| `max_outage_s` | The limit: the longest allowed outage in seconds. Give a nonnegative limit for every named stream. |
| `log` | Optional step-specific log rules. |

If the final state requires a cable to be up, add an explicit `up` step to measure the cable coming back before the final state check. The Small lab's [cable YAML](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/tests/small/bond-member-loss.yaml) and [reboot YAML](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/tests/small/switch-reboot.yaml) show complete steps and explain the holds and limits.

### Typed actions

Use one action per step. A traffic fault or other change that a later step must end needs that step within the same test. One power loss can be active at a time, and `power_on` must name the same node, list or group as its `power_off`.

| Keys inside `action` | Effect and evidence |
| --- | --- |
| `observe: true` | Measure traffic and any step checks in the current state. |
| `reboot: switch1` | Request a RouterOS reboot over SSH, verify a fresh boot and wait for every lab state check to pass. |
| `power_off: switch1`, then `power_on: switch1` | Pause the named RouterOS CHR guest and take carrier down on its data cables. On `power_on`, reset and resume the guest, bring carrier back, verify a fresh boot and wait for every lab state check to pass. |
| `power_off: [switch1, switch2, client1]`, then `power_on` with the same list | Power off several nodes in one step, such as a whole site. The value can also name an inventory group that is not a lab node. Networka pauses every RouterOS CHR guest, sets every data cable of the listed nodes down and takes carrier down on the guest NICs that face them. A Linux node keeps running with all its data cables down, so its kernel keeps state such as bond and neighbour entries. On `power_on`, it resets and resumes every guest, brings all cables back, verifies a fresh boot of each guest and then waits for every lab state check to pass. |
| `impair: client1:eth1` with `loss_percent`, `delay_ms`, or both | By default (`direction: out`), add an impairment to traffic leaving the given point. Use `in` for traffic leaving the far end or `both` for both ends. Set optional `jitter_ms` with delay. Verify the installed values and read its counters. Repeat `impair` with `clear: true` to remove the impairment and put back the default queue. |
| `cut_ping: stream-name` with `at: client2:eth3` | Drop the named stream’s IPv4 echo requests at the cable ingress. Repeat `cut_ping` with `clear: true`. Replay checks the filter counters and whether the capture brackets the cut as one continuous outage. |
| `silence_lacp: client1:eth1` with `bond: bond0` | Drop outbound LACP slow-protocol frames at the named Linux bond member. Repeat `silence_lacp` with `clear: true`. Verify the drops, that the member loses eligibility while carrier stays up, and that eligibility comes back. |
| `active_member: client3:bond0` with `member: eth2` | Select a member of an active-backup Linux bond. Repeat the action with the original member. Replay uses the bond state and the captures on the switches' TAP interfaces to verify movement. |
| `silence_host: client3:bond0` with `relearn_s: 1` | Suppress egress from both members of an active-backup Linux bond. Repeat `silence_host` with `clear: true`. Replay checks wire silence, flooding and resumed delivery against the stated relearn deadline. |

Reading the impairment back proves the queue settings. For a ping-level delay check, add `delay_stream: stream-name` to the action that sets `delay_ms`. Replay compares the median round-trip time in the source capture before, during, and after the delay.

Use the test's optional `flood` mapping to add a flood check, which verifies that broadcast and unknown-unicast frames do not return to their sender. It names `from` (the Linux LACP bond), `to` (a receiver point), the IPv4 `broadcast` and `unicast` destinations, and the reserved `unicast_mac`. The source must start with a permanent neighbor for the unicast destination. Networka verifies that each frame sent during the quiet window reaches the receiver once and counts repeats across the source's two physical bond members through the sender cutoff.

The optional `watch_host_entries` mapping names an `interval_s`, RouterOS `bridge`, `devices` and `macs`. Networka samples those bridge entries during the steps and reports the measured sampling interval. Each step needs an in-window sample and each watched entry must remain present in every sample used to judge that step.

A `log` contains `must` or `must_not` lists. Each rule names a `switch` or `every` and matches its `text` as a case-insensitive substring of a device message. A whole-test rule covers each switch's start-to-end marker interval. A step rule requires marker coverage of the entire step. Marker records themselves are excluded. A required message must appear on every targeted switch and a forbidden message must be absent from each.

## What the run measures

1. For a lab with switch logging, Networka records the collector offset and sends each switch a start marker. Switches are identified by marker-capable devices in the lab, the inventory's `switches` group, and individual rule targets. Unrecognised senders or a missing marker invalidate log coverage. The collector may create its file on the first message.
2. The starting state check must pass before Networka starts the traffic or takes an action. When it does not pass, Networka runs none of the steps and the test is `error`. It captures both ends of every stream, each action cable and the extra points that the configured actions and checks need. Pings run every 100 ms to resolve outages shorter than a second. Each stream must show a first reply within 5 s.
3. The quiet window starts at the last stream's first reply. Networka checks 3 s of clean traffic before the first action, allowing three fast LACP messages for bonds to settle. A clean window has no outage or duplicate and at least `floor(window duration / 110 ms) − 1` delivered pings per stream. The count allows 10% scheduling variation and one boundary ping. An unclean quiet window yields `error` before any action.
4. Networka changes the cable in its network namespace and, for an end on a QEMU guest, through the guest's QEMU monitor. It waits up to 1 s for carrier confirmation on an end it did not set directly, because a virtual cable normally changes carrier within milliseconds.
5. For a reboot, Networka verifies that the target is one `mikrotik_chr` node with a `mikrotik_routeros` inventory entry at its live topology management address. It reads native RouterOS uptime and sends `:execute {/system reboot}` once over pooled SSH. After dispatch it checks for the SSH banner before trying an authenticated uptime read, with 5 s between tries to give RouterOS time to accept new sessions. The step must prove a lower uptime that fits within the monotonic time since dispatch and pass every lab state check within `recovery_deadline_s`. A missed recovery deadline ends the remaining steps with `error`. When the deadline is missed after a traffic fault or a power loss ends and all steps have started, the report still measures them through the sender cutoff, and the final state check and closing window give `error`. The stream limits cover dispatch, recovery, and the hold after recovery.
6. The closing window starts when the last hold ends and runs through the final device state check to the sender cutoff. The state check begins after 0.6 s, one ping interval plus the reply allowance. Closing uses the same clean-traffic rule as the quiet window. Loss or duplicates here give `fail`. Too few delivered pings to check continuity give `error`. After stopping the senders, Networka keeps the captures open for the final 500 ms reply allowance.
7. On completion, error, or interruption, Networka tries to undo outstanding cable, queue, filter, bond and guest changes, then stops the senders and captures. When a cleanup repair has a corresponding `up` step with required log rules, Networka waits up to that step's `hold_s` for those messages before it writes the end markers. It allows 1 s for the collector to receive the end markers on the local management network. The lab stays deployed for inspection or teardown using the lab's startup instructions.

## Verdict

The request and reply must appear in captures at both ends of the stream. A stream to a fixed address is measured at its source only: a ping counts as delivered when its reply returns to the source capture in time. Networka matches pings by ICMP identifier, sequence, and echoed payload. Linux ping can reuse a sequence after a send error with a fresh timestamp in the payload. A reply must return within 500 ms because a lab path in its expected state answers within milliseconds. An outage spans consecutive undelivered pings. Its lower bound is the time from the first to the last lost request. Its upper bound is the time between the delivered requests immediately before and after it, when both exist. An outage counts in every step it overlaps. The report shows the total lost pings separately from the longest outage used for the limit.

| Step verdict | Condition |
| --- | --- |
| `pass` | Every stream’s upper bound is within its limit and the applicable state, action and log checks pass. |
| `fail` | A lower bound exceeds its limit, or reaches it with a lost ping, because traffic stopped for longer than that lower bound. A zero limit allows no lost or late ping. A duplicate ping or broken log rule also fails the step. |
| `error` | The bounds cannot decide the limit or the required evidence is unusable. |

A send pause longer than 450 ms leaves too much of the 500 ms reply deadline unobserved, allowing half a ping interval as margin. A longer pause inside a step with a nonzero limit affects only that step. When the pause is no longer than the limit, the step reports the pause as the upper bound of its outage, because an outage hidden by the pause cannot exceed it. A longer pause gives the step `error`. A step with a 0 s limit, the quiet window and the closing window keep the 450 ms rule for the whole run. A wall-clock change of 50 ms against the monotonic clock makes packet and event times unreliable. A missing stream capture or kernel-reported capture drops, a sender or stream capture that exits early, captures at the two ends of a stream that disagree and a cable that Networka could not bring back also invalidate the measurement. Additional captures of action cables are diagnostic.

| Exit | Meaning |
| --- | --- |
| `0` | `pass`. The evidence verifies the applicable state, traffic, action and log checks. |
| `1` | `fail`. A check found an actual violation, such as an excessive outage or a broken log rule. |
| `2` | `error`. A run ended early, the starting state check did not pass, evidence could not decide a check, the input or lab was unusable, or replay found a result mismatch. |

A failed check takes precedence over a check that gives `error` in a completed run and when combining verdicts across files. A recorded run error makes that run `error`. Networka saves `error` and re-raises an interrupt received during evidence collection. On Linux the interrupted command can exit `130` for SIGINT, while replay exits `2`.

A preflight error can exit before creating a test directory. For example, a stopped collector node fails preflight. A running collector that receives no markers leaves a saved run whose log rules give `error`.

## Results summary

`nw test summary <file>` writes a lab repository's results table and chart from runs saved by `nw test run --save`. It rewrites the lines between a `<!-- results:start -->` line and a `<!-- results:end -->` line in a Markdown file and writes an SVG chart of the worst outage per lab and mode. The same runs give byte-identical output. A missing run directory, test folder or `result.json` exits 2 and names the path.

```yaml
markdown: README.md
chart: docs/diagrams/results-worst-outage.svg
chart_alt: Worst traffic outage per lab with RSTP off and on, against its limit
pass_icon: docs/diagrams/result-pass.svg
fail_icon: docs/diagrams/result-fail.svg
caption: RSTP on has the MLAG pair as root. `nw test` live runs of 27 November 2026
modes: [RSTP off, RSTP on]
rows:
  - lab: Small
    topology: One MLAG pair
    link: tests/small/README.md
    cells:
      RSTP on:
        runs: [test-results/small-rstp.20261127T061300Z]
        link: tests/small-rstp/README.md
  - lab: Medium two-pair-strict
    topology: Two MLAG pairs + `lacp-strict`
    label: Two MLAG pairs, lacp-strict
    link: tests/medium-two-pair-strict/README.md
```

Paths are relative to the summary file. Links written into the Markdown are relative to the Markdown file. `modes` orders the table columns and the chart sub-rows. A row gives the `lab` name, Markdown `topology` text and `link` to the lab README. The chart shows `label`, or by default the topology without backticks. A mode missing from `cells` shows as not run. A cell lists its `runs` and may `link` its passed count. Each run path is a `--save` directory, whose test folders all count, or a single test folder. A test name listed twice in one cell exits 2. The closing sentence names the summary file and links it. The caption is followed by the ping interval from the results.

The cell shows the number of `pass` tests out of all tests and the number of `error` tests. Its verdict is FAIL when a test failed, PASS when none failed and at least one passed, and ERROR otherwise. The worst outage is the stream outage with the largest upper bound among tests that are not `error`, skipping outages the report marks `error`. It shows the bounds, the stream limit, the step name and the stream's source and destination nodes from the run's own `lab.yaml` copy. The chart marks a PASS cell with a green circle and a FAIL cell with a red square. A dashed line marks the most common limit, and a mark with another limit names it.

## Saved evidence

| Entry | Content |
| --- | --- |
| `test.yaml`, `lab.yaml` | Inputs used for this run. |
| `state-before/`, `state-after/`, `step-state/<step-number>/` | Saved device replies for the state checks that ran. |
| `recovery/<step-number>/<try-number>/` | Device replies from each try of the full state check during recovery. |
| `topology-data.json` | Copy of the topology data that replay of a power loss uses to verify data cables. |
| `host-entries/<switch>.jsonl` | Timed raw replies for a configured host-entry watch. |
| `captures/`, `streams/` | Per-point pcaps, tcpdump diagnostics and per-stream ping output. |
| `events.jsonl`, `syslog.log` | Timed actions and the collector lines for this run. |
| `result.json` | Machine-readable verdict, checks, measured outages, limits and matching log lines. |
| `report.md` | Verdict, traffic limits and measured outages, action evidence, matching switch log lines, and the chronology of state checks, actions and replies. |

Replay uses the saved YAML and replies, regenerates `report.md`, and compares the freshly judged result byte for byte with the saved `result.json`. It leaves `result.json` and the raw evidence unchanged. A matching result keeps the saved verdict and its exit code. A difference exits 2 even if the verdict word is the same. For older runs without a sender cutoff, the report marks the end of traffic coverage at the last step.
