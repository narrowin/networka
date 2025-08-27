# Networka

Modern async Python toolkit for network device automation.

## 60-second success

Goal: run a command against a device without creating any files.

```bash
nw run --platform mikrotik_routeros 192.0.2.10 "/system/identity/print" --interactive-auth
```

Expected output (trimmed):

```
Interactive authentication mode enabled
Username: admin
Password: ********
Executing on 192.0.2.10: /system/identity/print
name="MikroTik"
Command completed successfully
```

Short install video (30s):

[asciinema placeholder – will be embedded here]

## Key features

- Multi-vendor automation (MikroTik, Cisco, Arista, Juniper, …)
- Async concurrent operations for speed and scale
- Flexible configuration (YAML/CSV), tags and groups
- Vendor-aware sequences and backups
- Rich CLI output with selectable output modes
- Type-safe internals (mypy), clean CLI (Typer + Rich)

## Get started

Start with the Quickstart, then explore the User guide for config, environment variables, output modes, results, and more.

Python 3.11+ is required.
