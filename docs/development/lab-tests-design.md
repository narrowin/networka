# Lab test engine

The lab repository defines a containerlab topology, device configuration, and
YAML tests. Networka runs the tests and judges their saved evidence. The
[lab test guide](../lab-tests.md) describes the YAML, supported actions, output,
and command usage.

- `lab.py` loads the deployed topology, verifies that the lab owns each node and
  that it runs, and starts traffic and capture processes on the lab machine in node
  namespaces. Cable actions resolve the peer from the topology and use QEMU
  monitor commands for guest-backed interfaces.
- `labtest.py` validates the two YAML files and binds inventory names to lab
  addresses. A live run writes timed events, device replies, and switch
  logs. It records the sender cutoff for closing-window judgment and collects
  switch log markers after cable cleanup.
- `lab_reboot.py` validates the named target against the live node and
  calls the RouterOS intent adapter over the pooled SSH session. Replay
  checks the command record, verifies native uptime against dispatch time, and
  judges the state check try that passed again from its saved intent evidence.
- `lab_power.py` takes the topology's data cables down and pauses the named CHR guest.
  It proves recovery with QEMU replies, carrier reads, a fresh RouterOS
  uptime and the same full state check after recovery as a reboot.
- `lab_faults.py` owns impairment queues and the typed ping and LACP filters. It
  checks command reads and counters and uses stream captures to verify a
  `cut_ping` outage or a configured round-trip delay check.
- `lab_mobile.py` moves or silences an active-backup Linux bond. Replay checks
  the selected member and available forwarding evidence from the captures on TAP interfaces
  and hosts.
- `lab_flood.py` runs the flood check: it watches broadcast and unknown-unicast
  frames for repeat sightings across the sender's physical bond members.
- `lab_watch.py` samples RouterOS bridge host entries during timed steps and
  rechecks the samples against the confirmed cable and step boundaries.
- `traffic.py` matches each ping across both captures by identifier, sequence
  and echoed payload. The send timestamp in the payload distinguishes retries
  that reuse a sequence. Measured send times bound each outage.
- `lab_summary.py` reads saved results and their `lab.yaml` stream
  directions and renders the results table and worst-outage chart for a lab
  repository README.
- `commands/test.py` exposes [run, replay and summary](../reference/cli.md#nw-test).
  Both call the same judge and report renderer. The judge
  reads the copied YAML, events, captures, device replies and switch log from
  the run directory.
