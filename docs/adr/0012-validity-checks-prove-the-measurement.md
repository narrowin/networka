# Validity checks prove the measurement

Networka proves that a measurement is sound with validity checks of its own: a steady sending pace on every stream, no capture drops reported by the kernel, captures and senders that run to the end, a clean quiet window before the first action and a stable clock.
A failed validity check gives ERROR, not FAIL, because the measurement and not the network is in doubt.
A lab needs no extra cable or stream of its own to prove the measurement.

## Why

The first MLAG suite proved its measurement with a bypass cable between two hosts and calibration tests that cut it.
On 2026-11-26 the operator rejected that for the Small lab: "In the lab, we have always a management network".
Checks of the run's own captures, senders and clock cover the same ground in every lab, without changing the topology.

## Consequences

A test that wants to show a known outage is measured correctly uses a traffic fault, such as dropping the pings of one stream, whose replay checks that the capture brackets the cut as one continuous outage.
