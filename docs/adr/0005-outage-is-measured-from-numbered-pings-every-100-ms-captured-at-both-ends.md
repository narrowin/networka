# Outage is measured from numbered pings every 100 ms, captured at both ends

Every stream sends one numbered ICMP ping every 100 ms, and Networka captures it at both ends.
It matches each ping across both captures by identifier, sequence and echoed payload, and a reply must return within 500 ms.
An outage is bounded below by the first and last lost ping and above by the delivered pings around it.
A step whose outage the bounds cannot decide is ERROR, never PASS.
A stream to a fixed address, such as a VRRP address, is captured at its source only.

## Why

A short ping summary, such as five pings before and after a fault, misses an outage that ends between them, and it misses a failure on only one hash path.
A 100 ms interval resolves outages well under one second.
Capturing at both ends tells which direction lost the ping.

## Considered options

- **IRTT or another sequenced UDP stream.** Not used: numbered ICMP captured at both ends gives the direction and the timing, and it also reaches a switch or VRRP address that cannot run a server.
- **mtr or traceroute for timing.** Rejected: they show the path, not when forwarding stopped.

## Consequences

Every limit in every lab is written for this cadence, so changing the interval means recalibrating every limit.
A report gives lost pings together with the interval and the time they stand for.
How the bounds and the validity checks work is in the [lab test guide](../lab-tests.md#verdict).
