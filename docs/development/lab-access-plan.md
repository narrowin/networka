# Linux lab nodes over SSH: plan for step 1

This plan covers the first build step of [Lab tests with Networka](lab-tests-design.md).

## Problem

Networka reaches a device over SSH. The switch nodes of a containerlab lab have an SSH server. The Linux nodes of the MLAG labs have none, so Networka's checks cannot run on them.

## Decision

A Linux lab node gets an SSH server and a login. Networka gets no second way to connect.

A first version of this step added a `docker exec` transport to Networka. It worked in a live lab. It was dropped because it gave Networka a second connection path with its own rules for credentials, errors and timeouts. With SSH on the node, the lab and a production network are reached in the same way.

## What is built

### In the lab repository

- The Linux image of the MLAG labs gets an SSH server. The node starts it when it boots.
- The node accepts a login as `root`, because the LACP details in `/proc/net/bonding` are only shown to `root`.
- The login is a fixed lab credential, as the CHR nodes have one.
- The Networka configuration of the lab lists the Linux nodes with that login.

### In Networka

- The `docker` transport and its import rule are removed from the branch.
- A bond member without an LACP partner gives `fail` for the `lacp_member` check on RouterOS. It gave `error` before. The first live run showed that one broken cable gave `fail` on the Linux side and `error` on the switch side.
- `nw run` with one command prints the reason when the command fails. It printed nothing before.

## What is not built in this step

- Captures and streams. They come in step 2.
- Any change to how the MLAG suite reads its clients today.

## Proof

The step is done when all of the following hold.

1. Networka's own checks pass. These are ruff, mypy, pytest and the strict docs build.
2. On a fresh Small MLAG lab, one intent file checks the two CHR nodes and a Linux client, all over SSH. The client items are `bond_members`, `lacp_member`, `bond_member` and `ping`. The run passes, and `nw intent replay` gives the same result.
3. With one bond member of that client taken down, the run fails on the items for that member, on the client and on the switch. No item gives `error`. The replay gives the same result.
4. A `ping` from the client to an unused address gives `fail` and exit status 1. A Linux node that cannot be reached gives `error` and exit status 2 with one clear line.
5. The MLAG baseline case still passes on the lab with the new image.
6. The change is on `main` in both repositories, and the branch is deleted.
