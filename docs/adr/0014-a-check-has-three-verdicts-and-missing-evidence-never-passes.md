# A check has three verdicts, and missing evidence never passes

Every check, step, run and test ends as PASS, FAIL or ERROR.
FAIL is a confirmed wrong state; ERROR means the evidence cannot decide; PASS needs evidence that shows the expected state.
Absence needs positive proof: a normalizer reports an empty value only from a reply that shows the object exists, and an empty, mismatched or failed reply is ERROR.
Across the items of a completed run the overall verdict is fail-first: any FAIL makes the run FAIL, and the ERROR items stay listed with their reasons.

## Why

Archived MLAG runs showed a reply lost to an SSH timeout reported like a real `no-link`, and an interrupted run reported zero lost pings.
A check that could not see the state has not verified it.
ANTA, pyATS and nornir-salt use the same three outcomes.
Fail-first keeps a confirmed failure from being hidden by an item that could not be checked.

## Considered options

- **Pass and fail only**, where a missing field or a timeout passes or fails silently. Rejected.
- **Error-first overall**, where one unverifiable item hides a confirmed failure. Rejected.

## Consequences

A test whose starting state check fails is not a completed run; it is ERROR, as [ADR 0003](0003-a-lab-test-pushes-no-configuration-and-state-checks-prove-the-lab-state.md) records.
Exit codes follow the verdict: 0 for PASS, 1 for FAIL and 2 for ERROR.
