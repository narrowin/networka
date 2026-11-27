# A reboot is the switch's own reboot, and a power loss pauses the guest and withdraws carrier

A reboot action sends the switch's own reboot command once over its session, `:execute {/system reboot}` on RouterOS.
It proves a fresh boot by a lower uptime that fits within the time since dispatch, and then waits for every state check to pass within the step's recovery deadline.
A power loss action pauses each named VM guest through its QEMU monitor and withdraws carrier on all its data cables; a Linux node keeps running with all its data cables down.
At the end of the power loss Networka resets and resumes each guest, restores the cables, proves a fresh boot and waits for every state check.

## Why

The two faults reach the network differently.
In a reboot the data links can keep carrier while the switch is gone, so its neighbours notice only through protocol timeouts.
In a power loss every neighbour sees its cable go down at once.
On 2026-11-25 the operator asked whether the reboot test was needed at all: "So yeah, we should use the power loss case then, not do the reboot at all, right?"
On 2026-11-27 he kept both as separate tests: "No, I guess reboot is fine from the speed, so that is okay."

## Considered options

- **Power loss only.** Rejected: it drops the fault where the switch is gone while its links still show carrier.
- **Freeze the guest when its management address stops answering after a reboot.** Rejected: the freeze lands while the switch still shuts down, which is a hung switch, a different fault.

## Consequences

Power loss works only for VM guests behind a QEMU monitor, such as RouterOS CHR, and for Linux nodes.
A recovery that misses its deadline stops the remaining steps with ERROR.
