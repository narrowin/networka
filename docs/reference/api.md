# API Reference

!!! info
The API reference is not yet implemented. Coming soon.

<!-- Enable this when the API docs are ready to publish
::: network_toolkit
-->

## Planned coverage

- Configuration models (`network_toolkit.config.*`) — Pydantic v2 models for devices, groups, sequences, and general settings
- Device session (`network_toolkit.device.DeviceSession`) — SSH session management, command execution, file transfer
- Exceptions (`network_toolkit.exceptions.*`) — typed error hierarchy for connection, auth, timeouts, execution, configuration
- Results management (`network_toolkit.results.*`) — structured results, storage, and output formatting
- Commands/operations (`network_toolkit.commands.*`) — reusable operations backing the CLI (run, upload/download, backup, firmware)
- Common utilities (`network_toolkit.common.*`) — logging, output manager, and helpers used across modules

See Development guide for contribution details: `docs/development.md`.
