# A test is a YAML file of exact values, and running it needs no AI

A test file and a lab file are YAML data that Networka validates and runs; a test has no code of its own.
The expected state, the actions, the holds and the limits are all in those two files.
An intent file is a YAML list of items with exact expected values: no operators, expressions, tags, skip rules or OpenConfig paths.
Checks compare normalized fields for equality, and selection and arithmetic belong to whoever writes the file.
Every verdict comes from plain code that compares saved evidence with these files, so the same evidence always gives the same verdict.
No AI decides a verdict, and Networka has no AI dependency.

## Why

On 2026-11-25 the expected state of the MLAG tests was spread over Python runners and several files.
A proposal to keep YAML optional was rejected; the operator answered: "Isn't that how we describe the intent?"
He added the same evening: "running the tests shouldn't need AI, right?"
Exact values keep a file readable by the person who has to trust its verdict, as NUTS does with its plain expected values.
Replay needs a judge that gives a byte-identical result on the same evidence ([ADR 0006](0006-replay-judges-saved-evidence-again-and-must-give-a-byte-identical-result.md)), which a model cannot promise.

## Considered options

- **A Python or pytest file per test.** Rejected: a new lab would need code, and the expected state would hide in it.
- **Expressions such as `is-gt`, tag filtering or an OpenConfig model**, as ANTA and others offer. Rejected: device-state intent needs equality only, and expressions make a file harder to read.
- **An AI-decided verdict.** Rejected: it cannot be replayed to the same result, and nobody can say which expectation decided it.

## Consequences

A test that needs a new kind of action or check needs a Networka change first ([ADR 0001](0001-networka-holds-all-test-logic-and-a-lab-is-only-a-description.md)).
Both formats are described in the [lab test guide](../lab-tests.md) and in [intent verification](../intent.md).
