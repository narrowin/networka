# Impairments use tc netem in the node's namespace

Networka adds packet loss and delay with `tc qdisc ... netem` inside the network namespace of the node, on the interface of the given point.
netem acts only on traffic that leaves an interface, so the action takes a direction: out from the given point, in as egress at the far end, or both.
Networka reads the installed queue back to prove its settings and restores the default queue when the impairment ends.
Filters that drop the pings of one stream or LACP frames use `tc` in the same way.

## Why

The operator prefers the lab tool's own features to hand-written commands.
On 2026-11-26 `containerlab tools netem` was measured on the lab machine and exited with an error on its kernel, while `tc` netem in the node's namespace worked.

## Considered options

- **`containerlab tools netem`.** Rejected while it fails on the lab machine's kernel.
- **Scripts in each lab repository.** Rejected ([ADR 0001](0001-networka-holds-all-test-logic-and-a-lab-is-only-a-description.md)).

## Consequences

The root runner needs `tc` from iproute2 in its `PATH`.
When `containerlab tools netem` works on the lab machine, this decision can be revisited.
