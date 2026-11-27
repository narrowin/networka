# Customer upgrade validation

Status: Option 2 implemented and verified using saved nw run results on containerlab

## Current implementation

The operator selected Option 2 from `structured-diff-options.md`: integrate
DeepDiff into the existing `nw diff`, using saved `nw run` results and keeping
the first increment small. This supersedes the earlier interface-specific
`nw intent record/compare` prototype, which has been removed. Existing
`nw intent run/replay` commands and lab behavior are preserved.

Use `general.results_format: json` and `nw run --store-results` to save native
JSON replies. Compare two saved result files or directories with:

```bash
uv run nw diff collection-001 collection-002 --structured --key name
```

Names identify arbitrary saved collections, not upgrade steps. DeepDiff 9.2.1
compares complete native payloads. `--key` is optional and requires unique
row identities. Explicit repeatable `--exclude-path` options apply only during
comparison and are displayed. Output describes differences, without assigning
a network PASS/FAIL. Exit codes are 0 unchanged, 1 changed and 2 error.

Human output uses DeepDiff's compact colored view of the same comparison,
with unchanged nested objects collapsed. Terminals without color use the
library's explicit text descriptions. JSON mode emits structured changes and
a comparison summary. The CLI owns rendering; the API retains the comparison
and its JSON-compatible changes. See `deepdiff-live-20261127/compact-verification.md`
for the saved-result demonstration and local checks.

Live evidence and verification are in
`deepdiff-live-20261127/verification.md`.

## Outcome

Use Networka to check a customer's network before and after network operating
system upgrades. Rehearse the checks in containerlab and run the applicable
checks against physical production devices, where access to Linux systems is
usually absent.

## Agreed scope

On 27 November 2026 the operator accepted both recommendations from the scope
round:

- Build the customer upgrade checks first. Improve the shared intent/test
  implementation where the concrete workflow requires it.
- Preserve existing `nw intent` and `nw test` commands, YAML files, verdict
  rules and replay behavior for current saved evidence, including existing
  lab result and report stability.
- The customer inventory will be supplied through the operator's inventory
  source. Its contents and export interface have not yet been inspected.
- The operator's team is responsible for performing the upgrades. Whether
  they use other Networka capabilities to do so is undecided; upgrade
  execution is separate from the validation design.
- The primary validation requirement is to record the existing device state
  and establish whether it remains the same after the upgrade. Interface
  operational state is an explicit example. Additional tests may be included;
  their scope is not yet agreed.
- Compare selected operational properties rather than complete command text.
  Interface state, speed and MTU should remain the same, as should LACP and
  VLAN membership and routing neighbours where applicable. Software version
  must match the intended release. Keep uptime and cumulative counters as
  evidence without requiring equality. Missing or unreadable required
  readings give ERROR.
- Keep existing defects visible separately from unexpected changes. An
  unchanged required link that is down still fails its check. The operator
  may explicitly acknowledge an accepted exception; it is not silently
  treated as correct.
- Compare after each upgrade group has recovered, before the operator
  proceeds to the next group, and compare across the agreed network scope
  at the end. Recovery conditions and observation duration remain open.
- Require repeated agreement on the properties being compared before
  accepting the before-upgrade state and after recovery. Retain the readings
  and flag instability. Reading intervals and duration remain to be selected
  for the actual platforms and protocols.
- Accepted differences and existing defects name the affected devices and
  properties, with a reason. Unexpected differences remain visible until
  reviewed; broad exclusions must not hide unrelated changes.
- A state record is the saved set of device readings. A state comparison
  compares selected device state between two state records. The operator
  accepted these terms in interview question 11; they are in `GLOSSARY.md`.
- Keep the state records from before the first upgrade unchanged as the
  reference throughout the work. Later records do not silently replace them;
  explicitly accepted differences apply during comparison.
- After each upgrade group, include its devices and their agreed dependencies
  in the state comparison. The final state comparison covers the whole agreed
  network scope. Define the membership before starting.
- Device-state comparison is the required first deliverable. Device-originated
  pings are optional, explicitly selected checks. State which paths they
  cover; application acceptance remains a separate responsibility.
- Start with a small usable implementation and extend it iteratively. Avoid
  introducing abstractions before the workflow needs them.
- Read the device's native structured data as JSON where supported, retaining
  the replies in the state record. This follows ADR 0013 and the existing
  RouterOS intent readers. Collecting a table and choosing which properties
  to compare are distinct responsibilities; recording must not require a
  hand-written expected value for every property.

The operator confirmed the simple one-switch example and explicitly requested
its implementation. The broader requirements above remain subsequent work.

## Superseded one-switch prototype

```bash
uv run nw intent record switch1 --save before
# The operator upgrades switch1.
uv run nw intent record switch1 --save after
uv run nw intent compare before after
```

Record one RouterOS device's native interface JSON and Ethernet monitor
replies in `record.json`. Compare interface membership and selected stable
properties by interface name, without accessing devices or overwriting
existing records. Retain native replies, including failed readings, as
evidence. Missing required data is ERROR, not unchanged. Existing intent
commands, formats and lab replay contracts stay unchanged.

The first increment reads each table/monitor once and reports differences.
Repeated stability readings, group scope, broader table/platform support,
planned-change handling and integrated acceptance checks remain subsequent
increments. This narrowing follows the operator's request to implement the
simple example first rather than design the full upgrade workflow upfront.

## First increment verification

Checked with Python 3.15.2 using the repository's networka-verify instructions.
Use `UV_CACHE_DIR=/private/tmp/networka-uv-cache` for these local commands;
the default uv cache is outside the writable sandbox.

- Ruff lint and format checks passed for `state.py`, `commands/intent.py`
  and the RouterOS intent module.
- Mypy passed for those three source files.
- `uv run --locked --no-sync pytest tests/test_intent.py
  tests/test_platforms_mikrotik.py tests/test_cli.py -q`: 66 passed.
- The documented development CLI walkthrough passed, including configuration
  generation, inventory loading, help and error handling.
- Actual `nw intent compare` invocations using anonymous-pipe JSON inputs
  returned exit 0 for unchanged, 1 for a link changing down and 2 for unusable
  evidence. No fixture files or new automated suite were created.
- Direct local comparisons checked added/removed interfaces, an already-down
  interface, counter and row-order differences, and missing Ethernet evidence.
- Regenerated the CLI reference. Strict MkDocs build passed, with existing
  navigation notices and a theme end-of-life notice.
- `git diff --check` passed.

Those initial checks did not access live devices. The operator subsequently
requested the live containerlab verification recorded below.

## Live containerlab verification

On 27 November 2026, deployed an isolated `state-record-20261127` lab in the
OrbStack `mlag-external` VM, using the pinned CHR image. Read the actual
RouterOS version as `7.26beta7`. Other sessions' labs were not changed.

- Recorded `switch1` as `live-20261127/before-working/record.json` and again
  as `after-unchanged/record.json`; comparison returned PASS, exit 0.
- Disabled only `demo-bridge` on this disposable switch. Recorded
  `after-change/record.json`; comparison returned FAIL, exit 1, showing
  `disabled: false -> true` and `running: true -> false`, plus MTU fields
  no longer reported for the disabled bridge. Other interfaces were unchanged.
- Restored the bridge and recorded `after-restored/record.json`; comparison
  returned PASS, exit 0. Saved the actual changed and restored CLI output as
  `live-20261127/changed-output.txt` and `restored-output.txt`.
- The virtual Ethernet management interface reports link state but no speed.
  Adjusted the normalizer to compare speed only where reported, retaining
  the complete native reply. Repeated recording succeeded after that change.
- Ruff passed and the 38 existing intent and RouterOS checks passed after
  the adjustment. This is CHR verification, not physical switch verification.

Destroyed only the isolated verification lab using its topology file, retaining
the state records and command output for inspection.

## Existing implementation

- `nw intent` collects device state and judges saved observations against
  explicit expectations. Its current platform adapters support RouterOS and
  Linux. See [intent verification](../../docs/intent.md).
- `nw test` uses those state checks within ordered containerlab tests, adding
  actions, traffic measurement and evidence. See
  [lab tests](../../docs/lab-tests.md).

## Open decisions

- Device roles, software releases, functions and access details derived from
  the supplied inventory; platform support must be checked against them.
- Exact coverage by device role, including additional properties beyond
  those agreed above.
- Required network properties, exception handling and how expected changes
  are declared.
- Available production traffic and application evidence.
- Comparison rules, observation periods, and criteria for proceeding or
  restoring the previous software.
- Concrete command and file interfaces and the first implemented coverage.
- Necessary changes to the existing implementation and their verification.

## Proposed command walkthrough

This earlier multi-device proposal was superseded by the approved one-switch
first increment above. It is retained here only as context for later scope.

Suppose the inventory group `group-a` contains the switches being upgraded
and their agreed dependencies:

```bash
uv run nw intent record group-a --config networka.yaml --save records/before
# The operator performs the upgrade.
uv run nw intent record group-a --config networka.yaml --save records/after
uv run nw intent compare records/before records/after --save comparisons/group-a
```

The first two commands read the devices and save their native JSON replies.
The third reads saved records without accessing devices. It reports selected
properties that changed, such as an interface's operational state, while
accounting for declared expected changes. Existing `nw intent run` remains
the way to check explicit expected values, such as a required link being up.

The proposed first implementation's coverage is still open. The operator has
emphasized native structured queries rather than manually specifying an
expected value for each property to be recorded.

## RouterOS JSON support

RouterOS introduced `:serialize` and `:deserialize` in the 7.13 release series;
the `json.no-string-conversion` option was added in the 7.17 release series.
Networka's current RouterOS readers use that option. Verify the required
commands and options on both the starting and intended releases.

Sources: [MikroTik 7.13 announcement](https://forum.mikrotik.com/t/v7-13rc-testing-is-released/171577),
[MikroTik 7.17 announcement](https://forum.mikrotik.com/t/v7-17beta-testing-is-released/179003),
and [RouterOS readers](../../src/network_toolkit/platforms/mikrotik_routeros/intent.py).

## Comparison and checks

Keep the answer to "what changed?" separate from "does this meet the expected
state?". For example, a link down before and after is unchanged, but still
fails a check requiring it to be up. The operator accepted this distinction
in interview questions 6 to 8.

## Terminology

Both glossaries reserve baseline for fault-free traffic with a zero outage
limit. Use state record and state comparison for this workflow, as defined
in the Networka glossary. State records retain device replies as evidence;
their storage format has not yet been designed.
