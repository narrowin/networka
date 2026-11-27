# A test keeps one SSH session per device

During a test Networka opens one SSH session per device and reuses it for every state check, marker and command.
It does not log in again for each command.
A session that loses its connection is closed and replaced, and its command is not sent again, because the device may already have run it.

## Why

On 2026-11-26 a measurement on RouterOS 7.26beta7 showed that RouterOS refuses password logins for about 30 s after a quick series of SSH logins.
A login per command would make state checks fail on a working switch.

## Considered options

- **A new login per command.** Rejected for the reason above.
- **A local shell through `docker exec`.** Rejected ([ADR 0010](0010-networka-reaches-every-lab-node-over-ssh-at-the-address-containerlab-assigned.md)).

## Consequences

After a reboot the old session is dead, so Networka waits for the SSH banner and leaves 5 s between logins before it reads the uptime.
The same reuse is how `NetworkaClient` works outside tests.
