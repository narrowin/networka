# Interactive Credentials Feature

## Overview

Use the `--interactive-auth` flag (or the short `-i`) when you want the CLI to prompt for credentials at runtime instead of reading them from files or environment variables. Interactive prompts are available on the commands that establish device sessions: `nw run` and `nw info`.

## How It Works

When `--interactive-auth` is provided, the CLI prompts once for a username and password, then applies those values to every targeted device in the invocation. Prompts respect the configured output mode, so messages stay quiet when `--output-mode raw` is active.

### Credential Resolution Order

The project resolves credentials using the following priority chain (highest first):

1. Interactive overrides supplied via `--interactive-auth`
2. Device credentials defined in the modular configuration (`user` / `password` fields or device overrides)
3. Device-scoped environment variables (`NW_USER_<DEVICE>`, `NW_PASSWORD_<DEVICE>`)
4. Group-level credentials from the configuration or matching environment variables (`NW_USER_<GROUP>`, `NW_PASSWORD_<GROUP>`)
5. Default environment variables (`NW_USER_DEFAULT`, `NW_PASSWORD_DEFAULT`)

>.env files in the config directory are loaded automatically, but exported environment variables always win over values from a file.

### Environment Variable Naming

Use the `NW_<TYPE>_<TARGET>` pattern with uppercase names and hyphens replaced by underscores. Common examples:

```text
NW_USER_DEFAULT=admin
NW_PASSWORD_DEFAULT=changeme

# Device-specific overrides
NW_USER_SW_ACC1=opsuser
NW_PASSWORD_SW_ACC1=s3cr3t

# Group-level overrides
NW_USER_ACCESS_SWITCHES=opsuser
NW_PASSWORD_ACCESS_SWITCHES=groupsecret
```

These variables can live in the environment or in a `.env` file alongside the configuration tree.

## Examples

```bash
$ nw info sw-acc1 --interactive-auth
Interactive authentication mode enabled
Username [admin]: opsuser
Password: ********
Will use username: opsuser

Device: sw-acc1
├─ Host: 192.168.1.10
├─ Port: 22
├─ Credentials: Interactive (opsuser)
└─ Groups: access_switches

$ nw run sw-acc1,sw-acc2 '/system/clock/print' -i
Interactive authentication mode enabled
Username [admin]: opsuser
Password: ********
Will use username: opsuser

Executing on sw-acc1,sw-acc2: /system/clock/print
✓ Command completed successfully on sw-acc1
✓ Command completed successfully on sw-acc2
```

Interactive prompts respect cancellations. Press `Ctrl+C` at any prompt to abort without making changes.
