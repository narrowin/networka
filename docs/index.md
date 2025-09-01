---
template: home.html
title: Networka
---

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

!!! tip "Pro tip"
    Use `--help` with any command to see all available options and examples.

## Installation options

=== "uv (Recommended)"

    ```bash
    uv tool install git+https://github.com/narrowin/networka.git
    ```

=== "pip"

    ```bash
    pip install git+https://github.com/narrowin/networka.git
    ```

=== "pipx"

    ```bash
    pipx install git+https://github.com/narrowin/networka.git
    ```

## What makes it different?

- **Zero configuration needed** - Just run commands against IP addresses
- **Async by design** - Built from ground up for concurrent operations  
- **Vendor intelligence** - Platform-specific optimizations and commands
- **Type safety** - Full mypy coverage for reliable automation
- **Rich terminal** - Beautiful output with progress indicators and colors

[Get started with configuration :material-arrow-right:](configuration.md){ .md-button .md-button--primary }
[Browse examples :material-arrow-right:](examples/recipes.md){ .md-button }

Start with the Installation, then explore the User guide for config, environment variables, output modes, results, and more.

Python 3.11+ is required.
