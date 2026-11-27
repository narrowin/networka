# The Textual TUI is retired

Networka has no terminal user interface.
The internal Textual TUI, its tests and its dependencies were removed in commit `eb04095`; the `nw` CLI, its Rich output and the Python library stay.

## Why

The TUI had no console entry point and no user guide, but it made Textual a runtime dependency and kept its own run, cancel and output paths beside the CLI and the library.
Its own configuration loader also disagreed with the CLI about which configuration and sequences it found.
On 2026-11-25 the operator decided: "Okay, drop the TUI. ... Keep the CLI and Rich."

## Considered options

- **Keep a minimal internal browser.** Rejected: its use beyond the CLI's own inspection commands was not shown.
- **Make one narrow TUI workflow useful.** Rejected: it needed configuration parity, one run path and result handling across several modules for an unproven benefit.

## Consequences

Old documents that mention the TUI describe history, not a feature.
