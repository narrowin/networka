# Arista EOS

Supported identifiers: `arista_eos`

## Highlights

Status: coming soon. Vendor-specific documentation for firmware management, backups, and sequences is being prepared.

## Quickstart

### Run

```bash
nw run --platform arista_eos 198.51.100.30 "show version" --interactive-auth
```

### Validate (expected output, trimmed)

```
Interactive authentication mode enabled
Username: admin
Password: ********
Executing on 198.51.100.30: show version
Arista ...
Command completed successfully
```

## Examples

```bash
nw run eos1 "show version"
```
For now, you can browse example user sequences under `docs/examples/user_sequences/arista_eos/` and run ad-hoc commands:
