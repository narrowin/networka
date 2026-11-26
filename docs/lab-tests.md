# Lab tests

`nw test run` checks a containerlab lab before and after a sequence of cable changes or RouterOS switch reboots. It measures IPv4 ping streams and checks switch logs against the test’s rules. `nw test replay` judges the saved evidence again with the lab offline.

## Run and replay

Start the lab using its own startup instructions. Run `nw test run` as root on the Linux host running its Docker containers. The host needs `docker`, `ip`, `nsenter`, `tcpdump`, `tshark`, and `ping` from iputils for explicit ICMP identifiers. Pass the directory containing the generated `topology-data.json` to `--lab`. All nodes must be running, and the Networka inventory must supply SSH access for state checks, reboots, and log markers. An inventory device named after a lab node can omit its host to use the node's management address.

Follow the [Small lab README](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/tests/small/README.md) to start its qualified native CHR lab. With an installed `nw` available to `sudo`, run these commands from the Small lab repository root. For a reboot run, change the first line to `case_name=switch-reboot`. The README also shows how to run the same tests with `uv` from a Networka checkout.

```sh
case_name=bond-member-loss
out=$(mktemp -d)
sudo nw test run "tests/small/$case_name.yaml" \
  --lab tests/small/clab-small-mlag --config tests/small/devices.yml --save "$out"
sudo nw test replay "$out/$case_name"
```

Each input test gets a directory named after its filename without the extension under `--save`. An existing nonempty evidence directory is refused. Pass multiple test files to run them in order. Use `--interactive-auth` to prompt for SSH credentials. Replay needs `tshark` and permission to read the evidence and write the report. [CLI reference](reference/cli.md#nw-test) · [Measured Small lab runs](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/docs/walkthrough-networka-tests.md)

## Files that define a test

A lab file holds its stream directions, state checks and optional switch log. A point is a containerlab node and its interface, written `node:interface`.

| Lab field | Meaning |
| --- | --- |
| `streams` | Each entry gives a unique `name`, a `from` point and a `to` point. Pings target the destination interface's IPv4 address. File order assigns the ICMP identifiers. |
| `state` | Each entry gives a `statement`, optional `source` and device `checks`. [Intent check format](intent.md) |
| `switch_log` | Collector file relative to the deployed lab directory. Each line starts with an RFC 3339 receive timestamp and the switch name, followed by the message. Required for log rules. |

A test file gives its `name`, `purpose`, `lab` file path relative to the test and ordered `steps`. It may include a `source` and whole-test `log` rules.

| Step field | Meaning |
| --- | --- |
| `name`, `expected` | Step title and expected behaviour. |
| `cable`, `state` | For a cable change, supply one endpoint and its required state, `down` or `up`. |
| `action.reboot`, `wait_healthy_s` | For a reboot, name one RouterOS CHR switch in the `action` mapping and set a positive deadline in seconds to prove a new boot and recover the lab state. |
| `hold_s` | Seconds to observe after carrier confirmation or proven reboot recovery. |
| `max_outage_s` | Longest allowed traffic stop in seconds. Give a nonnegative limit for every named stream. |
| `log` | Optional step-specific log rules. |

If the final state requires a cable to be up, add an explicit `up` step to measure its return before the final state check. The Small lab's [cable YAML](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/tests/small/bond-member-loss.yaml) and [reboot YAML](https://github.com/narrowin/mikrotik-mlag-testsuite/blob/main/tests/small/switch-reboot.yaml) show complete steps and explain the holds and limits.

A `log` contains `must` or `must_not` lists. Each rule names a `switch` or `every` and matches its `text` as a case-insensitive substring of a device message. A whole-test rule covers each switch's start-to-end marker interval. A step rule requires marker coverage of the entire step. Marker records themselves are excluded. A required message must appear on every targeted switch and a forbidden message must be absent from each.

## What the run measures

1. For a lab with switch logging, Networka records the collector offset and sends each switch a start marker. Switches are identified by marker-capable devices in the lab, the inventory's `switches` group, and individual rule targets. Unrecognised senders or a missing marker invalidate log coverage. The collector may create its file on the first message.
2. All device preconditions must pass before Networka starts the traffic or takes an action. It captures both ends of each stream and each action cable. Pings run every 100 ms to resolve stops smaller than a second. Each stream must show a first reply within 5 s.
3. The quiet window starts at the last stream's first reply. Networka checks 3 s of clean traffic before the first action, allowing three fast LACP messages for bonds to settle. A clean window has no outage or duplicate and at least `floor(window duration / 110 ms) − 1` delivered pings per stream. The count allows 10% scheduling variation and one boundary ping. An unclean quiet window yields `error` before any action.
4. Networka changes the cable in its network namespace and, for QEMU endpoints, through the guest's QEMU monitor. It waits up to 1 s for carrier confirmation on an end it did not set directly, because a virtual cable normally changes carrier within milliseconds.
5. For a reboot, Networka verifies that the target is one `mikrotik_chr` node with a `mikrotik_routeros` inventory entry at its live topology management address. It reads native RouterOS uptime and sends `:execute {/system reboot}` once over pooled SSH. After dispatch it checks for the SSH banner before trying an authenticated uptime read. The 5 s wait between attempts gives RouterOS time to accept returning sessions. The step must prove a lower uptime that fits within the monotonic time since dispatch and pass every lab state check within `wait_healthy_s`. A recovery timeout stops the remaining steps with `error`. The stream limits cover dispatch, recovery, and the hold after recovery.
6. The closing window starts when the last hold ends and runs through the final device state check to the sender cutoff. The state check begins after 0.6 s, one ping interval plus the reply allowance. Closing uses the same clean-traffic rule as the quiet window. Loss or duplicates here give `fail`. Too few deliveries to verify continuity give `error`. After stopping the senders, Networka keeps the captures open for the final 500 ms reply allowance.
7. On completion, error, or interruption, Networka attempts to restore cables it took down and stops the senders and captures. When a cleanup repair has a corresponding `up` step with required log rules, Networka waits up to that step's `hold_s` for those messages before it writes the end markers. It allows 1 s for the collector to receive the end markers on the local management network. The lab stays deployed for inspection or teardown using the lab's startup instructions.

## Verdict

The request and reply must appear in captures at both stream endpoints. Networka matches pings by ICMP identifier, sequence, and echoed payload. Linux ping can reuse a sequence after a send error with a fresh timestamp in the payload. A reply must return within 500 ms because a healthy lab path answers within milliseconds. An outage spans consecutive undelivered pings. Its lower bound is the time from the first to the last lost request. Its upper bound is the time between the delivered requests immediately before and after it, when both exist. An outage counts in every step it overlaps. The report shows the total lost pings separately from the longest stop used for the limit.

| Step verdict | Condition |
| --- | --- |
| `pass` | Every stream's upper bound is within its limit and all log rules pass. |
| `fail` | A lower bound exceeds its limit, or reaches it with a lost ping, because traffic stopped for longer than that lower bound. A zero limit allows no lost or late ping. A duplicate ping or broken log rule also fails the step. |
| `error` | The bounds cannot decide the limit or the required evidence is unusable. |

A send pause longer than 450 ms leaves too much of the 500 ms reply deadline unobserved, allowing half a ping interval as margin. A wall-clock change of 50 ms against the monotonic clock makes packet and event times unreliable. A missing stream capture or kernel-reported capture drops, a sender or stream capture that exits early, inconsistent endpoint observations and failed cable restoration also invalidate the measurement. Additional captures of action cables are diagnostic.

| Exit | Meaning |
| --- | --- |
| `0` | `pass`. The evidence verifies the state, traffic, and applicable reboot and log checks. |
| `1` | `fail`. A check found an actual violation, such as a failed device precondition, excessive outage, or broken log rule. |
| `2` | `error`. A run stopped, evidence could not verify a check, the input or lab was unusable, or replay found a result mismatch. |

A failed check takes precedence over an unverified check in a completed run and when combining verdicts across files. A recorded run error makes that run `error`. Networka saves `error` and re-raises an interrupt received during evidence collection. On Linux the interrupted command can exit `130` for SIGINT, while replay exits `2`.

A preflight error can exit before creating a case directory. For example, a stopped collector container fails preflight. A running collector that receives no markers leaves a saved run with unverified switch logs.

## Saved evidence

| Entry | Content |
| --- | --- |
| `test.yaml`, `lab.yaml` | Inputs used for this run. |
| `state-before/`, `state-after/` | Saved device observations for the state checks that ran. |
| `recovery/<step-number>/<attempt>/` | Device observations from each full-state check during reboot recovery. The native uptime readings and the reboot command's reply are in `events.jsonl`. |
| `captures/`, `streams/` | Per-point pcaps, tcpdump diagnostics and per-stream ping output. |
| `events.jsonl`, `syslog.log` | Timed actions and the collector lines for this run. |
| `result.json` | Machine-readable verdict, checks, measured stops, limits and matching log lines. |
| `report.md` | Verdict, traffic limits and measured stops, reboot proof, matching switch log lines, and the chronology of state checks, actions and observations. |

Replay uses the saved YAML and observations, regenerates `report.md`, and compares the freshly judged result byte for byte with the saved `result.json`. It leaves `result.json` and the raw evidence unchanged. A matching result keeps the saved verdict and its exit code. A difference exits 2 even if the verdict word is the same. For older runs without a sender cutoff, the report marks the end of traffic coverage at the last step.
