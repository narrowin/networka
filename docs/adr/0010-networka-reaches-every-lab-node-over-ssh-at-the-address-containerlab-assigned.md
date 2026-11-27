# Networka reaches every lab node over SSH at the address containerlab assigned

Networka reads device state and runs commands on every lab node it checks over SSH, switches and Linux hosts alike.
It has no second way in, such as `docker exec`.
An inventory device named after a lab node may omit its address, and Networka then takes the node's management address from the `topology-data.json` that containerlab wrote when it deployed the lab.
Host keys of lab nodes are neither checked nor stored.

## Why

A first version added a `docker exec` transport for Linux nodes, and it worked in a live lab.
On 2026-11-26 the operator rejected it: "it's overcomplicating things if you actually go with the Docker fallback."
A second connection path has its own rules for credentials, errors and timeouts, and with SSH on the node a lab and a production network are reached in the same way.
Committed addresses only duplicate what containerlab already knows, and replay reads the saved topology.
A lab is redeployed many times a day and gets new host keys each time; the operator said on 2026-11-26: "we don't want you to store the SSH host keys. It just doesn't make sense."

## Consequences

Every Linux image in a lab needs an SSH server and a login, as `root` where the state it reads is shown only to root.
Traffic, cable and capture actions still run on the lab machine through `nsenter` as root, not over SSH ([ADR 0004](0004-lab-actions-run-on-containerlab-only.md)).
