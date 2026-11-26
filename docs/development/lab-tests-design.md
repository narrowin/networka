# Lab test engine

The lab repository defines a containerlab topology, device configuration, and
YAML tests. Networka runs the tests and judges their saved evidence. The
[lab test guide](../lab-tests.md) describes the YAML, supported actions, output,
and command usage.

- `lab.py` reads the deployed topology, binds inventory devices to the lab, and
  starts host-side processes in the node namespaces. Cable actions change and
  confirm carrier at both ends.
- `labtest.py` runs device preconditions, checks an initial quiet window, and
  runs the steps in order. It checks device state again and measures traffic
  through the final sender cutoff. Cleanup restores cables before the final
  switch log markers.
- `lab_reboot.py` uses the platform adapter to dispatch a typed reboot over the
  pooled SSH connection. It records native uptime evidence of a new boot and
  waits for the lab state to recover within the step deadline.
- `traffic.py` matches each ping across both captures by identifier, sequence
  and echoed payload. The send timestamp in the payload distinguishes retries
  that reuse a sequence. Observed send times bound each stop.
- `commands/test.py` exposes run and replay. Both use the same verdict and
  report functions. Replay rebuilds `report.md` and compares the recomputed
  bytes of `result.json` with the original using the saved evidence alone.
