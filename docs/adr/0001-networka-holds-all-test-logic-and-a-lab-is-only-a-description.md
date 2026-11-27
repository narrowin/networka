# Networka holds all test logic, and a lab is only a description

On 2026-11-26 the operator decided that running a test, judging included, is one function of Networka: `nw test run` runs it and `nw test replay` judges it again.
A lab repository holds only what describes its lab: the containerlab topology, the configuration its nodes boot with, a Networka inventory, the lab file, the test files and their limits.
A new lab needs no Python code of its own.

## Why

The MikroTik MLAG lab was the first user, and a Cumulus lab and others need the same engine.
On 2026-11-26 the operator said: "The MLAG lab is one incarnation of many labs".
The first port split the work: Networka read device state, while the judge, the pings and the captures stayed in the lab repository.
The operator rejected that split because half of each test lived in each repository.

## Considered options

- **The judge stays in the lab repository, and Networka only reads device state.** Rejected: it kept two places for one test.
- **Move the MLAG lab into Networka.** Rejected: a lab is one user of the engine, not part of it.
- **A large framework such as pyATS, Genie or NUTS.** Rejected. On 2026-11-26 the operator said: "these are huge frameworks. We want to keep it simple to the point." Networka keeps a fixed set of actions and checks and adds one only when a test needs it.

## Consequences

A change to how a test runs or is judged is a Networka change, released and then pinned by each lab repository.
The first lab repository is [narrowin/mikrotik-mlag-testsuite](https://github.com/narrowin/mikrotik-mlag-testsuite).
