# Juniper JunOS

Supported identifiers: `juniper_junos`

Status: coming soon. Vendor-specific documentation for firmware management, backups, and sequences is being prepared.

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
