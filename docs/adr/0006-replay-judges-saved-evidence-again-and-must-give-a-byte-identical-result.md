# Replay judges saved evidence again and must give a byte-identical result

Every run saves the evidence needed to judge it again with the lab offline: the test and lab files as run, the device replies of every state check, the packet captures, the timed events and the switch log.
`nw test replay` judges that evidence again, writes `report.md` again and compares the new `result.json` byte for byte with the saved one.
It exits 2 on any difference, even when the verdict word is the same.
`nw intent replay` judges a saved intent run again in the same way.

## Why

A verdict is only as good as the evidence behind it, and nobody can rerun a past lab state.
Replay shows which expectation decided a verdict, and it lets a change to the judge be checked against every saved run without a lab.
During the port of the MLAG suite, replay showed that the old and new judges agreed on the same evidence, and it ran negative checks such as forcing `forwarding: false` in a saved reply.

## Consequences

The judge must be deterministic: no timestamps of its own in `result.json` or `report.md`, and a fixed order everywhere ([ADR 0002](0002-a-test-is-a-yaml-file-of-exact-values-and-running-it-needs-no-ai.md)).
Whatever a run keeps must be enough for replay to reach the same result, which binds [ADR 0008](0008-a-run-keeps-only-the-capture-slices-that-prove-its-verdict.md).
