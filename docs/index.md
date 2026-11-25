---
template: home.html
title: Networka
---

## Quick start {#quick-start}

[Install Networka from the checkout](getting-started.md#installation) and
inspect a packaged RouterOS sequence.

```bash
nw info system_info --vendor mikrotik_routeros
```

Replace the example IP with your RouterOS device and enter its credentials
when prompted.

```bash
nw run 192.0.2.10 system_info --platform mikrotik_routeros --interactive-auth
```

See how to [run a reusable sequence](running-commands.md),
[save the output](results.md), and
[compare it with a baseline](reference/cli.md#nw-diff).

<div align="center">
  <img src="assets/gifs/networka-setup.gif" alt="Networka Setup Demo" width="100%"/>
  <p><em>Networka setup and command execution demonstration</em></p>
</div>

## Key features

- Multi-vendor automation (MikroTik, Cisco, Arista, Juniper, …)
- Flexible configuration (YAML/CSV), tags and groups
- Containerlab-friendly: consume generated `nornir-simple-inventory.yml` directly
- Vendor-aware sequences and backups
- Rich CLI output with selectable output modes
- Type-safe internals (mypy), clean CLI (Typer + Rich)

## Networka vs the alternatives

| | Networka | Ansible | Nornir |
|---|---|---|---|
| Primary interface | CLI commands | YAML playbooks | Python scripts |
| Time to first command | Seconds after install | After writing playbook + inventory | After writing Python script |
| Learning curve | Familiar CLI patterns | YAML, Jinja2, modules | Python programming |
| Execution | Concurrent by default | Sequential by default | Depends on implementation |
| Best for | Daily operations, ad-hoc commands | Infrastructure-as-code, compliance | Custom automation frameworks |

Networka is built for network engineers who want to run commands now. Ansible excels at declarative infrastructure-as-code. Nornir shines when you need full Python programmability. Different tools, each great at what they do.

## Project Model

- **License**: Apache 2.0 - unrestricted use
- **Cost**: Free, no paid features.
- **Development**: Open source, accepting contributions
- **Support**: Community via GitHub issues
- **Maintenance**: [narrowin](https://narrowin.ch/en/about.html) engineering team and community contributors

## Installation

Start with the [Installation Guide](getting-started.md#installation), then explore the User guide for config, environment variables, output modes, results, and more.

Python 3.15 or later is required.
