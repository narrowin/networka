# A lab test pushes no configuration, and state checks prove the lab state

A lab test changes no configuration of its lab; `nw run`, uploads and firmware commands stay outside `nw test`.
Each lab boots into the state its tests need from the configuration of its nodes.
The lab file names state checks that Networka runs before a test, at its end, and after a reboot or power loss before the hold goes on.
A test whose starting state check does not pass takes no action, and its verdict is ERROR, not FAIL.

## Why

The first MLAG suite changed bridge settings over SSH before each test and read them back.
On 2026-11-26 the operator decided that configuration belongs to the lab, not to the test engine: "it should not be living in [Networka] to actually push config".
A test needs evidence that the lab is in the known state when it starts and that it came back to that state.
A check that reads the state proves the starting point without changing it.
A failed starting state means the fault was never tried, so the test cannot say whether the network passed or failed it; that is ERROR.

## Considered options

- **Config push as a Networka feature.** Rejected: it makes the engine responsible for every vendor's configuration.
- **One configuration, changed per test over SSH.** Rejected: the state a test ran in would depend on the order of earlier tests.
- **FAIL for a failed starting state**, as a failed check is FAIL elsewhere. Rejected: a FAIL claims the network failed the fault, which was never injected.

## Consequences

A lab that needs other settings is a lab of its own, and a lab that needs a playbook runs it from its own repository between deploy and `nw test run`.
A test that leaves the lab broken shows up as ERROR in the starting state check of the next test.

## What is not built

`nw test run` still gives FAIL, exit 1, when the starting state check fails, as the [lab test guide](../lab-tests.md#verdict) says.
