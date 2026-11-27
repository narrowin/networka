# Customer upgrade validation

Status: Interview in progress

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

The proposed implementation remains subject to the operator confirming shared
understanding at the end of the design interview.

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
- Terminology for the saved observations before and after an upgrade.
- Necessary changes to the existing implementation and their verification.

## Comparison and checks

Keep the answer to "what changed?" separate from "does this meet the expected
state?". For example, a link down before and after is unchanged, but still
fails a check requiring it to be up. The operator accepted this distinction
in interview questions 6 to 8.

## Terminology

The MLAG suite glossary defines baseline as fault-free traffic with a zero
outage limit. A broader meaning for customer device observations has not been
agreed. No new glossary definitions have been accepted yet.
