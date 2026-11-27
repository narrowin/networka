# Lab actions run on containerlab only

The actions of a test, such as taking a cable down, rebooting or powering off a node, capturing packets and adding an impairment, work only on a lab that containerlab deployed.
Networka reads the deployed topology that containerlab writes, and acts on the lab machine through the network namespaces of the nodes and the QEMU monitor of each VM guest.
Networka itself is not limited to containerlab or to one vendor: its commands, sequences and intent checks work on any reachable device.

## Why

The actions need control of the machine that runs the lab, and containerlab is the only lab tool in use.
Supporting another lab tool would mean a second implementation of every action.
On 2026-11-26 the operator corrected a README that called Networka a containerlab tool: "It's not only tests for [containerlab]. It's just a testing framework".
Against a production network only the state and ping checks apply.

## Considered options

- **Other lab tools such as EVE-NG, GNS3 or plain Docker.** Rejected: no lab uses them.
- **A lab-neutral action layer.** Rejected: it would be built for one implementation.

## Consequences

`nw test run` runs as root on the lab machine and needs `docker`, `ip`, `nsenter`, `tcpdump`, `tshark`, `ping` and `tc` there.
