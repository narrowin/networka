# Configuration

This guide explains how to define devices, groups, and sequences for Networka. YAML is the preferred and most expressive format. CSV is supported mainly for users who manage inventories in spreadsheets on Windows. You can mix formats; use YAML by default and add CSV where it makes workflow sense.

Note on credentials: See Environment variables (TL;DR at the top) for how credentials are resolved and how to set defaults and overrides.

## Directory layout

Place configuration under the `config/` directory:

```
config/
├── config.yml                 # Optional global defaults
├── devices/                   # Device definitions (YAML or CSV)
│   ├── router1.yml
│   └── inventory.csv
├── groups/                    # Named groups and tag-based groups
│   ├── core.yml
│   └── teams.csv
└── sequences/                 # Reusable command sequences per vendor or shared
    ├── common.yml
    └── mikrotik_routeros.yml
```

Networka loads all files in these folders. Later files override earlier ones when names collide.

## Common concepts (applies to YAML and CSV)

- Device name: unique identifier used on the CLI (e.g., `nw run router1 ...`).
- Host: IP or DNS name to connect to.
- Device type: vendor/platform key (e.g., `mikrotik_routeros`, `cisco_iosxe`).
- Groups: explicit member lists and/or tag-based membership.
- Sequences: named sets of commands to run consistently.

Credentials come from environment variables; see Environment variables for details.

## YAML (preferred) {#yaml}

YAML gives you clarity, comments, nesting, and future-proofing. Prefer it for everything beyond one-off imports.

### Minimal device

```yaml
# config/devices/router1.yml
host: 192.0.2.10
device_type: mikrotik_routeros
tags: [edge, router]
```

### Group examples

```yaml
# config/groups/core.yml
name: core
description: Core network devices
members: [sw-01, sw-02]

---
# config/groups/edge.yml
name: edge
description: Edge devices
match_tags: [edge]
```

### Sequence example

```yaml
# config/sequences/common.yml
health_check:
  description: Basic health check
  commands:
    - /system/resource/print
    - /interface/print stats
```

## CSV {#csv}

Use CSV if your source of truth is a spreadsheet. It’s convenient for bulk imports. Keep it simple and map columns to the same concepts as YAML.

### Devices CSV

Required columns: `name`, `host`

Optional: `device_type`, `description`, `platform`, `model`, `location`, `tags` (semicolon-separated)

```csv
name,host,device_type,description,platform,model,location,tags
sw-01,192.168.1.1,mikrotik_routeros,Main Switch,mipsbe,CRS326,Rack A1,switch;core;critical
rtr-01,192.168.1.254,mikrotik_routeros,Edge Router,arm,RB4011,Closet,router;edge
```

### Groups CSV

Required: `name`, `description`

Optional: `members` (semicolon-separated), `match_tags` (semicolon-separated)

```csv
name,description,members,match_tags
core_switches,Core network switches,sw-01;sw-02,switch;core
edge_devices,Edge routers and firewalls,,edge;firewall
```

### Sequences CSV

Required: `name`, `description`, `commands` (semicolon-separated)

Optional: `tags` (semicolon-separated)

```csv
name,description,commands,tags
health_check,Basic health check,/system/resource/print;/interface/print stats,monitoring;health
```

## YAML vs CSV: differences at a glance

- Expressiveness: YAML supports comments, nesting, and complex structures; CSV is flat.
- Multi-valued fields: In YAML, use lists; in CSV, use semicolon-separated values.
- Merging/overrides: Both support file-level overrides by name; YAML is clearer for intent.
- Editing: YAML with version control vs. CSV with spreadsheets—choose per team.

Recommendation: Use YAML for long-term, reviewable configuration. Use CSV for quick imports or where spreadsheets are mandated.

## Mixing formats

Mixing is supported. If both YAML and CSV define the same device/group/sequence name, the later-loaded file wins according to filesystem order. Keep ownership clear to avoid surprises.

## Next steps

- Set credentials and defaults → Environment variables
- Run common tasks → Running commands
- Inspect outputs and control formatting → Results and Output modes

## Bootstrap configuration (CLI)

Use the built-in `config` commands to inspect and manage configuration from the CLI. See the CLI reference for the full command set and options.

- List known devices/groups: `nw list devices` / `nw list groups`
- Validate config against schema: `nw schema validate`

More: CLI reference → Configuration-related commands
