# Lab tests

A lab test takes cables of a containerlab lab down and back and measures how long traffic stopped. Networka checks the device state before and after, sends ping streams, captures packets, reads the switch logs and judges each step against the limits and log rules of the test file. Every run saves its evidence, and `nw test replay` computes the same result again without the lab.

The lab repository holds the topology, one lab file per lab and one test file per test. Networka holds the engine.

## What it needs

- A deployed containerlab lab and its lab folder, the `clab-<name>/` folder that containerlab writes.
- Root on the lab host, because Networka enters node namespaces and captures packets.
- `tcpdump`, `tshark`, `ping` and `nsenter` on the lab host.
- A Networka device list with the lab's node names, platforms and credentials. A device without `host` gets the management address of its node from the lab's `topology-data.json`.

A point is written `node:interface`, with the containerlab node name and the interface name inside that node's network namespace.

## Lab file

| Field | Required | Meaning |
| --- | --- | --- |
| `streams` | Yes | Ping streams, each with `name`, `from` and `to` as points. Every test of the lab runs all of them. |
| `state` | Yes | Statements, each with `statement`, an optional `source` and `checks` in the format of [intent verification](intent.md). Networka checks them before the first step and after the last step. |
| `switch_log` | No | The file the switches log to, relative to the lab folder. Log rules need it. |

A stream pings the IPv4 address of its `to` interface once every 100 ms. Its ICMP identifier is its position in the file.

## Test file

| Field | Required | Meaning |
| --- | --- | --- |
| `name` | Yes | Title shown in the result and written in the log markers. |
| `purpose` | Yes | What the test checks and why. |
| `source` | No | Where the expected behaviour comes from. |
| `lab` | Yes | The lab file, relative to the test file. |
| `log` | No | Log rules for the whole test. |
| `steps` | Yes | Ordered steps. |

A step has `name`, `cable` (one end as a point), `state` (`down` or `up`), `hold_s`, `max_outage_s` (a limit in seconds for every stream), `expected` and an optional `log`.

A `log` holds `must` and `must_not`, each a list of `switch` (a node name or `every`) and `text`. The text matches part of a line, ignoring case. A step's rules cover the step. The test's rules cover the time between the two markers of each switch.

## How a test runs

1. Networka notes the size of the switch log and has every RouterOS device log `networka <name> start`.
2. It checks the state. If the state does not pass, it changes no cable.
3. It captures at both ends of every stream and of every cable that a step changes, and starts the streams.
4. The quiet window starts at the first reply of every stream and lasts 3 s. A lost or duplicated ping there stops the test before any cable changes.
5. Each step sets its cable and waits `hold_s`. A change at a node that runs in QEMU also goes through the QEMU monitor, because only then does the guest see it. Networka confirms the carrier at the far end within 1 s.
6. After 0.6 s for the last replies, Networka checks the state again and has every RouterOS device log `networka <name> end`. It waits up to 1 s for the end markers and saves what the log gained as `syslog.log`.
7. It stops every process and sets every cable that is still down up again, also after an error or Ctrl-C. Then it judges and saves the result.

## Verdict

A ping is delivered when its request and reply appear at both ends of the stream and the reply comes within 0.5 s. A run of pings that were not delivered is an outage. Its lower bound is the time from the first to the last lost request. Its upper bound is the time from the last delivered request before it to the first delivered request after it. An outage counts in every step it overlaps.

Each stream in each step gets a verdict.

- A 0 s limit allows no lost and no late ping.
- `pass` when the upper bound is at most the limit.
- `fail` when the lower bound is above the limit, or equals it with a lost ping.
- `error` when the bounds straddle the limit.
- `fail` when a ping arrived twice.

A `must` rule fails when its text is missing, and a `must_not` rule fails when its text appears. A switch whose start or end marker is missing from `syslog.log` makes the test `error`, because a rule over a silent log would pass wrongly. The result lists the log lines per switch without judging them.

These checks give `error` and never `pass`.

- A stream end capture is missing, or the kernel dropped packets.
- A stream or its captures ended early.
- A cable could not be set up again.
- The wall clock and the monotonic clock of the lab host differ by 50 ms or more.
- A stream paused for more than 450 ms between two pings.
- The two ends of a stream saw different replies.
- The quiet window holds a lost or duplicated ping, or fewer pings than one per 110 ms less one.

Cable captures are diagnostics and never change the verdict. The test verdict is `fail` if anything fails, else `error` if anything is `error`, else `pass`. The exit status is 0, 1 or 2.

Every count of lost pings comes with its interval and the time it stands for, for example `24 pings lost at one ping every 100 ms, traffic stopped for 2.4 to 2.6 s`.

## Example

`lab.yaml`:

```yaml
streams:
  - name: client1-to-client2
    from: client1:bond0
    to: client2:bond0
state:
  - statement: Both switches show MLAG connected.
    checks:
      - name: switch1 MLAG connected
        device: switch1
        check: mlag
        params:
          bridge: bridge
        expected:
          connected: true
switch_log: syslog/switches.log
```

`bond-member-loss.yaml`:

```yaml
name: bond-member-loss
purpose: Client 1's cable to switch1 goes down and comes back, and client 1's traffic recovers.
lab: lab.yaml
log:
  must_not:
    - switch: every
      text: heartbeat timeout
steps:
  - name: Cable client1 to switch1 down
    cable: client1:eth1
    state: down
    hold_s: 5
    max_outage_s:
      client1-to-client2: 1
    expected: The cable goes down at both ends.
    log:
      must:
        - switch: switch1
          text: ether3 link down
  - name: Cable client1 to switch1 back
    cable: client1:eth1
    state: up
    hold_s: 7
    max_outage_s:
      client1-to-client2: 4
    expected: The cable comes back at both ends.
    log:
      must:
        - switch: switch1
          text: ether3 link up
```

```bash
sudo nw test run bond-member-loss.yaml --lab clab-small-mlag --config devices.yml --save out
nw test replay out/bond-member-loss
```

`nw test run` takes several test files and also `--interactive-auth`. It prints each statement, each step with each stream's lost pings and limit, each log rule and the test verdict.

## Evidence

Each test gets one folder under `--save`, named after the test file, which must not hold evidence yet.

| Entry | Content |
| --- | --- |
| `test.yaml`, `lab.yaml` | The files as they ran. |
| `state-before/`, `state-after/` | The two intent runs. |
| `captures/` | One pcap and tcpdump log per point. |
| `streams/` | One ping log per stream. |
| `events.jsonl` | Every action with its epoch and monotonic time. |
| `syslog.log` | The switch log lines of the test. |
| `result.json` | The verdict with every statement, step, log rule and validity check. |
| `timeline.tsv` | Seconds from the start of the quiet window, what happened, and a detail in words, with the switch log lines in time order. |

`nw test replay` computes `result.json` again from these files and writes `timeline.tsv` again. It needs `tshark` and no lab. It exits 2 when the result differs from the saved `result.json`.

## Limits of this version

- The only action is a cable down or up.
- A step cannot wait for a state, such as a rebooted node.
- Streams are unicast pings over IPv4.
