# Networka keeps its own runtime and does not adopt Nornir

Networka runs commands through its own executor and session pool around Scrapli.
It reads Nornir SimpleInventory files, including the one containerlab writes, into its own inventory without importing or depending on the Nornir runtime.

## Why

On 2026-11-25 the Nornir 3.7.0b1 beta and its typed tasks were studied.
The operator said that the Nornir runtime had shown no use so far, "since we got our own async runtime with around [Scrapli]".
Networka already returns typed run results and dispatches its own platform operations, and intent checks still need command-specific reading and deterministic comparison.

## Considered options

- **Adopt the Nornir runtime and task model.** Rejected: it adds a runtime beside the one Networka has, with no current need.

## Consequences

An external Nornir task can still hand its results to the same deterministic checks.
