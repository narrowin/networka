# The run writes its report, and nobody writes verdicts or numbers by hand

Every run writes `report.md` itself.
It starts with the verdict.
For every step and stream it shows the limit against the measured outage, the lost pings with the ping interval and the time they stand for, the log rules with the matching log line, and the chronology of checks and actions.
Machine data stays in `result.json`, `events.jsonl` and `syslog.log`.
`nw test summary` writes a lab repository's results table and chart from saved runs, so a table in a README is generated too.

## Why

On 2026-11-24 the MLAG reports were written by hand after the runs, and a reader could not tell a PASS from a FAIL.
On 2026-11-25 a ticket and a forum post carried hand-counted numbers that were wrong.
The operator said: "the tooling should actually write all those numbers. They should be measured during a test."

## Considered options

- **A hand-written summary per campaign.** Rejected: its numbers are not traceable to a run.
- **A tab-separated timeline as the human view.** Rejected as unreadable.

## Consequences

The report wording lives in Networka, so a change to it is a Networka release, and replay rebuilds `report.md` byte for byte ([ADR 0006](0006-replay-judges-saved-evidence-again-and-must-give-a-byte-identical-result.md)).
