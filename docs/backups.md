# Backups

Vendor-aware backup commands streamline configuration and system snapshots.

Common commands:

```bash
# Configuration export only
nw backup config device1

# Comprehensive backup (configuration + system data)
nw backup comprehensive device1

# Group operations with options
nw backup comprehensive office_switches --store-results
nw backup config device1 --delete-remote
```

Platform behavior:

- MikroTik RouterOS: creates `.rsc` (export) and optionally `.backup` (system)
- Cisco IOS/IOS-XE: collects configuration and system info outputs

Tips:

- Combine with `--store-results` to archive outputs in the results directory.
- Use device groups to back up multiple devices concurrently.
- See vendor pages for platform-specific details.
- Discover which vendors support backup operations in your build:

```bash
nw backup vendors
```
