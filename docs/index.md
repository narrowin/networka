---
template: home.html
title: Networka
---

## 60-second success {#quick-start}

First, install networka:

```bash
uv tool install networka
```

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

<div align="center">
  <img src="assets/gifs/networka-setup.gif" alt="Networka Setup Demo" width="100%"/>
  <p><em>Networka setup and command execution demonstration</em></p>
</div>

## Key features

- Multi-vendor automation (MikroTik, Cisco, Arista, Juniper, …)
- Flexible configuration (YAML/CSV), tags and groups
- Vendor-aware sequences and backups
- Rich CLI output with selectable output modes
- Type-safe internals (mypy), clean CLI (Typer + Rich)

## Project Model

- **License**: Apache 2.0 - unrestricted use
- **Cost**: Free, no paid features.
- **Development**: Open source, accepting contributions
- **Support**: Community via GitHub issues
- **Maintenance**: [narrowin](https://narrowin.ch/en/about.html) engineering team and community contributors

## Installation

Start with the [Installation Guide](getting-started.md#installation), then explore the User guide for config, environment variables, output modes, results, and more.

Python 3.11+ is required.
