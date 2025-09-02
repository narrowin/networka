---
template: home.html
title: Networka
---

## Naming & terminology

- Networka: the project and documentation
- nw: the command-line interface (CLI)
- nw-tui: the terminal ui based on textual (coming soon)

## 60-second success {#quick-start}

First, install networka:

```bash
uv tool install git+https://github.com/narrowin/networka.git
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
- Async concurrent operations for speed and scale
- Flexible configuration (YAML/CSV), tags and groups
- Vendor-aware sequences and backups
- Rich CLI output with selectable output modes
- Type-safe internals (mypy), clean CLI (Typer + Rich)

## Installation

Start with the Installation, then explore the User guide for config, environment variables, output modes, results, and more.

Python 3.11+ is required.
