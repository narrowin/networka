# Configuration

This guide explains how to define devices, groups, and sequences for Networka. YAML is the preferred and most expressive format. CSV is supported mainly for users who manage inventories in spreadsheets on Windows. You can mix formats; use YAML by default and add CSV where it makes workflow sense.

See [environment variables](environment-variables.md) for credential defaults and overrides.

## Directory layout

Use the platform-specific directory created by `nw config init`.
On Linux it is typically `~/.config/networka` and on macOS it is
`~/Library/Application Support/networka`. Place the modular files directly
in that directory, or pass your own directory with the command's
`--config` option.

```text
networka/
├── config.yml                 # Main configuration file
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
- `device_type` is the logical network OS used for definition and sequence selection, for example `mikrotik_routeros`.
- `platform` in inventory is an optional hardware architecture such as `arm` for firmware selection.
- Groups: explicit member lists and/or tag-based membership.
- Sequences: named sets of commands to run consistently.

For the active definition catalog, run `nw platforms list`.

## Using Nornir / Containerlab inventory (optional) {#nornir-inventory}

Networka can import inventory from a Nornir **SimpleInventory** file layout, including Containerlab’s generated `nornir-simple-inventory.yml`.

Configure this in `config/config.yml`:

```yaml
inventory:
  source: nornir_simple
  nornir_inventory_dir: /path/to/clab-<lab-dir>   # or a direct file path
  merge_mode: replace
```

See [Nornir & Containerlab inventory](nornir-inventory.md) for the full workflow and options.

## Syncing from SSH config {#ssh-config-sync}

Already have hosts in `~/.ssh/config`? Sync them to a YAML inventory:

```bash
nw sync ssh-config
```

See [SSH config sync](ssh-config-sync.md) for filtering, updates, and advanced usage.

## YAML (preferred) {#yaml}

YAML gives you clarity, comments, nesting, and future-proofing. Prefer it for everything beyond one-off imports.

### Minimal device

```yaml
# config/devices/router1.yml
devices:
  router1:
    host: 192.0.2.10
    device_type: mikrotik_routeros
    tags: [edge, router]
```

### Group examples

```yaml
# groups/groups.yml
groups:
  core:
    description: Core network devices
    members: [router1]
  edge:
    description: Edge devices
    match_tags: [edge]
```

### Sequence example

```yaml
# config/sequences/common.yml
sequences:
  router_summary:
    description: Basic RouterOS summary
    device_types: [mikrotik_routeros]
    commands:
      - /system/resource/print
      - /interface/print stats
```

Global definitions are a fallback after platform and device-local sequences.
See the [resolution order](multi-vendor-support.md#sequence-resolution-order).

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

## YAML vs CSV: differences at a glance

- Scope: Use YAML for sequences. Device and group inventories also support CSV.
- Expressiveness: YAML supports comments, nesting, and complex structures; CSV is flat.
- Multi-valued fields: In YAML, use lists; in CSV, use semicolon-separated values.
- Merging/overrides: Both support file-level overrides by name; YAML is clearer for intent.
- Editing: YAML with version control vs. CSV with spreadsheets—choose per team.

Recommendation: Use YAML for long-term, reviewable configuration. Use CSV for quick imports or where spreadsheets are mandated.

## Mixing formats

Device and group inventories can mix YAML and CSV. Keep each name in one file to make its source clear.

## Next steps

- Set credentials and defaults → Environment variables
- Run common tasks → Running commands
- Inspect outputs and control formatting → Results and Output modes

## Global settings (config.yml)

Use `config.yml` for settings that apply to all devices.

```yaml
general:
  ssh_strict_host_key_checking: true
  timeout: 30
  command_timeout: 60
```

Host-key checking defaults to disabled. See
[transport selection](transport.md) for how command sessions, tmux panes,
and SFTP apply the setting.

## Bootstrap configuration (CLI)

Use the built-in `config` commands to inspect and manage configuration from the CLI. See the CLI reference for the full command set and options.

- List known devices/groups: `nw list devices` / `nw list groups`
- Regenerate editor schemas: `nw schema install`
- Inspect schema status: `nw schema info`

More: CLI reference → Configuration-related commands
