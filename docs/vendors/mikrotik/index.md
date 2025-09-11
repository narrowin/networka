# MikroTik RouterOS

This guide explains how Networka works with MikroTik RouterOS devices: identifiers, supported operations, firmware upgrade/downgrade/RouterBOARD (BIOS) handling, backups, and built-in sequences.

## Quickstart

### Run

```bash
nw run --platform mikrotik_routeros 192.0.2.10 "/system/identity/print" --interactive-auth
```

### Validate (expected output, trimmed)

```
Interactive authentication mode enabled
Username: admin
Password: ********
Executing on 192.0.2.10: /system/identity/print
name="MikroTik"
Command completed successfully
```

### Sequence example

```bash
nw run router1 system_info
```

Expected output (trimmed):

```
router1: step 1/3 ... ok
router1: step 2/3 ... ok
router1: step 3/3 ... ok
Sequence completed successfully
```

### Next steps

- Learn more commands → Running commands
- Store outputs → Results and Output modes
- Backups and firmware → Backups
- Credentials → Environment variables

### Troubleshooting

- Use `--interactive-auth` for ad-hoc credentials
- Verify `device_type: mikrotik_routeros` when using named devices
- Increase timeouts if devices are slow

## Platform identifiers

- device_type: `mikrotik_routeros`
- Platform name: MikroTik RouterOS

## Supported operations

- Firmware upgrade: yes (`nw upgrade`) — file extension: `.npk`
- Firmware downgrade: yes (`nw downgrade`) — file extension: `.npk`
- BIOS/RouterBOARD upgrade: yes (`nw bios`)
- Configuration backup: yes (`nw config-backup` or `nw backup config`)

## Firmware management

Workflow used by Networka (RouterOS operations):

- Upload `.npk` package via SCP.
- Optional verification of packages with `/system/package/print`.
- Reboot with interactive confirmation to apply the package.

CLI shortcuts:

- Upgrade: `nw upgrade <device|group> <path/to/firmware.npk>`
- Downgrade: `nw downgrade <device|group> <path/to/older.npk>`
- RouterBOARD (BIOS): `nw bios <device|group>` — schedules `/system/routerboard/upgrade` then reboots.

Pre-checks: by default Networka runs the `pre_maintenance` sequence before firmware actions. Override with `--precheck-sequence` or skip via `--skip-precheck`.

## Backups

Two flavors exist:

- Config backup (text export): `nw config-backup <device|group>`
  - Creates an export (default: `/export file=nw-config-export`), then can download `nw-config-export.rsc` to `general.backup_dir`.
- Comprehensive backup: `nw backup comprehensive <device|group>`
  - Uses export plus system backup (e.g., `/system/backup/save name=nw-system-backup`).

You can also define/override sequences under config: `config/sequences/mikrotik_routeros/common.yml`.

## Built-in command sequences

RouterOS includes built-in sequences you can reference via `nw run <device> <sequence-name>` or include in your configuration. Examples include:

- `system_info`, `health_check`, `interface_status`, `routing_info`, `security_audit`

See file: `src/network_toolkit/builtin_sequences/mikrotik_routeros/common.yml`

Project configuration examples for global or device-level sequences live under: `config/sequences/mikrotik_routeros/common.yml`.

## Examples

Run commands and sequences:

```bash
nw run router1 "/system/identity/print"
nw run router1 system_info
```

Firmware and backups:

```bash
nw upgrade router1 ~/firmware/routeros-7.16.2-arm64.npk
nw bios router1
nw config-backup router1 --download --delete-remote
```

## Notes and tips

- Set `general.firmware_dir` and `general.backup_dir` in `config/config.yml`.
- Transport: SSH is recommended; interactive confirmations are handled by Networka.
- Results and logs can be stored under `results/` and `logs/` if enabled.
