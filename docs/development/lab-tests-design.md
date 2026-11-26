# Lab test engine

The lab repository defines a containerlab topology, device configuration, and
YAML tests. Networka runs the tests and judges their saved evidence. The
[lab test guide](../lab-tests.md) describes the YAML, supported actions, output,
and command usage.

- `lab.py` loads the deployed topology, verifies container ownership and
  running state, and starts host-side traffic and capture processes in node
  namespaces. Cable actions resolve the peer from the topology and use QEMU
  monitor commands for guest-backed interfaces.
- `labtest.py` validates the two YAML files and binds inventory names to lab
  addresses. The live flow writes timed events, device observations, and switch
  logs. It records the sender cutoff for closing-window judgment and collects
  switch log markers after cable cleanup.
- `lab_reboot.py` validates the named target against the live container and
  calls the RouterOS intent adapter over the pooled SSH connection. Replay
  checks the command record, verifies native uptime against dispatch time, and
  rejudges the successful recovery attempt from its saved intent evidence.
- `traffic.py` matches each ping across both captures by identifier, sequence
  and echoed payload. The send timestamp in the payload distinguishes retries
  that reuse a sequence. Observed send times bound each stop.
- `commands/test.py` exposes [run and replay](../reference/cli.md#nw-test).
  Both call the same evidence evaluator and report renderer. The evaluator
  reads the copied YAML, events, captures, and device and log observations from
  the run directory.
