# Juniper JunOS

Supported identifiers: `juniper_junos`

The packaged Scrapli catalog includes `juniper_junos`. Inspect the active
definition and available sequences with `nw platforms info juniper_junos`.
The operations registry has no vendor-specific firmware or backup implementation.

## Quickstart

### Run

```bash
nw run --platform juniper_junos 203.0.113.10 "show system information" --interactive-auth
```

### Validate (expected output, trimmed)

```
Interactive authentication mode enabled
Username: admin
Password: ********
Executing on 203.0.113.10: show system information
Hostname: ...
Command completed successfully
```

For now, you can run ad-hoc commands:

```bash
nw run router1 "show system information"
```
