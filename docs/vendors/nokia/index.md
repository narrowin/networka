# Nokia SR Linux

Supported identifiers: `nokia_srlinux`

Status: initial support available. Vendor-specific documentation for firmware management and backups will follow as platform operations are implemented.

## Quickstart

### Run

```bash
nw run --platform nokia_srlinux 198.51.100.40 "info from state system" --interactive-auth
```

### Validate (expected output, trimmed)

```
Interactive authentication mode enabled
Username: admin
Password: ********
Executing on 198.51.100.40: info from state system
...
Command completed successfully
```

## Notes

- Use `nw run <device> <sequence>` for sequences that include Nokia-specific commands when available.
- For configuration backups and firmware, refer to the unified commands and check support status with:
  - `nw backup --help`
  - `nw firmware vendors`
