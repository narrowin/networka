# Lab tests

`nw test run` checks a containerlab lab before and after a sequence of cable changes or RouterOS switch reboots. It measures IPv4 ping streams and checks switch logs against the test’s rules. `nw test replay` judges the saved evidence again with the lab offline.

## Run and replay

Run as root on the Linux lab host, with `tcpdump`, `tshark`, `ping` and `nsenter` available. The capture process uses the C locale for tcpdump's readiness and drop messages. Supply the lab directory that containerlab created and a Networka SSH inventory. Networka takes a device's management address from `topology-data.json` when the inventory omits its host.

```sh
sudo nw test run test.yaml --lab clab-example --config devices.yml --save out
sudo nw test replay out/test
```

Each input test gets a directory named after its filename under `--save`. Use a fresh output directory for each run. Replay needs `tshark` and permission to read the evidence and write the report. The run command accepts multiple test files and supports `--interactive-auth`. [Working Small lab and test](https://github.com/narrowin/mikrotik-mlag-testsuite/tree/main/tests/small)

## Files that define a test

A lab file holds its stream directions, state checks and optional switch log. A point is a containerlab node and its interface, written `node:interface`.

| Lab field | Meaning |
| --- | --- |
| `streams` | Each entry gives a unique `name`, a `from` point and a `to` point. Pings target the destination interface's IPv4 address. File order assigns the ICMP identifiers. |
| `state` | Each entry gives a `statement`, optional `source` and device `checks`. [Intent check format](intent.md) |
| `switch_log` | Collector file relative to the deployed lab directory. Required for log rules. |

A test file gives its `name`, `purpose`, `lab` file path relative to the test and ordered `steps`. It may include a `source` and whole-test `log` rules.

| Step field | Meaning |
| --- | --- |
| `name`, `expected` | Step title and expected behaviour. |
| `cable`, `state` | For a cable change, supply one endpoint and its required state, `down` or `up`. |
| `action.reboot`, `wait_healthy_s` | For a reboot, name one RouterOS CHR switch and give the deadline in seconds to prove a new boot and restore the lab state. Use a YAML mapping for `action`. |
| `hold_s` | Seconds to observe after carrier confirmation or proven reboot recovery. |
| `max_outage_s` | Longest allowed traffic stop in seconds for each named stream. |
| `log` | Optional step-specific log rules. |

A `log` contains `must` or `must_not` lists. Each rule names a `switch` or `every` and matches its `text` as a case-insensitive substring of a device message. A whole-test rule covers each switch's start-to-end marker interval. A step rule requires marker coverage of the entire step. Marker records themselves are excluded. A required message must appear on every targeted switch and a forbidden message must be absent from each.

## What the run measures

1. For a lab with switch logging, Networka records the collector offset and sends each switch a start marker. Switches are identified by marker-capable devices in the lab, the inventory's `switches` group, and individual rule targets. Unrecognised senders or a missing marker invalidate log coverage. The collector may create its file on the first message.
2. The device state must pass before Networka changes any cable. It starts captures at both ends of each stream and each action cable. One ping every 100 ms resolves an outage ten times more finely than a 1 s limit.
3. After every stream has replied, a 3 s quiet window allows three fast LACP messages for the bonds to settle. A clean window has no lost or duplicate ping and at least `floor(window duration / 110 ms) − 1` delivered pings per stream. The count allows 10% scheduling variation and one boundary ping. A failed precondition ends the run before the first action.
4. Networka changes the cable in its network namespace and, for QEMU endpoints, through the guest's QEMU monitor. It waits up to 1 s for carrier confirmation on an end it did not set directly, because a virtual cable normally changes carrier within milliseconds.
5. For a reboot, Networka checks the named device against the lab topology, reads its RouterOS uptime, and sends one background reboot command through its existing SSH client. It waits for the SSH banner without logging in on every probe. Five seconds between probes lets RouterOS accept returning sessions. Success requires a lower uptime than before the command, no greater than the elapsed time since dispatch, and passing observations for every lab precondition. The outage limit covers the reboot, recovery and subsequent hold.
6. After the last hold, Networka keeps measuring through the final state check and the sender cutoff. The state check begins after 0.6 s, one ping interval plus the reply allowance. The closing window requires continuous delivery with no duplicate ping. After stopping the senders, Networka keeps the captures open for the final reply allowance.
7. Cleanup restores cables that Networka took down. The collector saves its new lines through the end markers, allowing 1 s for UDP delivery on the local management network.

## Verdict

The request and reply must appear in captures at both stream endpoints. Networka matches each attempt by its ICMP sequence and echoed payload. Linux ping can reuse a sequence after a send error with a fresh timestamp in the payload. A reply must return within 500 ms because a healthy lab path answers within milliseconds. An outage spans consecutive undelivered pings. Its lower bound is the time from the first to the last lost request. Its upper bound is the time between the delivered requests immediately before and after it, when both exist. The outage counts in every step it overlaps.

| Step verdict | Condition |
| --- | --- |
| `pass` | Every stream's upper bound is within its limit and all log rules pass. |
| `fail` | A lower bound exceeds its limit, or reaches it with a lost ping, because traffic stopped for longer than that lower bound. A zero limit allows no lost or late ping. A duplicate ping or broken log rule also fails the step. |
| `error` | The bounds cannot decide the limit or the required evidence is unusable. |

A send pause longer than 450 ms leaves too much of the 500 ms reply deadline unobserved, allowing half a ping interval as margin. A wall-clock change of 50 ms against the monotonic clock makes packet and event times unreliable. A missing stream capture or kernel-reported capture drops, a sender or stream capture that exits early, inconsistent endpoint observations and failed cable restoration also invalidate the measurement. Additional captures of action cables are diagnostic.

The command exits 0 for `pass`, 1 for `fail` and 2 for `error`. An interrupted flow records an error. Otherwise a failed check takes precedence over an unverified check in the run verdict.

## Saved evidence

| Entry | Content |
| --- | --- |
| `test.yaml`, `lab.yaml` | Inputs used for this run. |
| `state-before/`, `state-after/` | Saved device observations for the state checks that ran. |
| `recovery/<step>/<attempt>/` | Device observations collected while waiting for a rebooted lab to recover. The native uptime readings and the fixed reboot command's reply are in `events.jsonl`. |
| `captures/`, `streams/` | Per-point pcaps, tcpdump diagnostics and per-stream ping output. |
| `events.jsonl`, `syslog.log` | Timed actions and the collector lines for this run. |
| `result.json` | Machine-readable verdict, checks, measured stops, limits and matching log lines. |
| `report.md` | Verdict, traffic limits and measured stops, reboot proof, matching switch log lines, and the chronology of state checks, actions and observations. |

Replay regenerates `report.md` from the raw evidence and compares the bytes of the freshly judged result with the saved `result.json`. A difference exits 2. For older runs that ended without a sender cutoff, the report marks the end of traffic coverage at the last step.
