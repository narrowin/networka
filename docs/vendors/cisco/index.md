# Cisco IOS / IOS-XE

This guide explains how Networka works with Cisco IOS and IOS-XE devices: identifiers, supported operations, firmware upgrade/downgrade handling, backups, and sequences.

## Quickstart

### Run

```bash
nw run --platform cisco_iosxe 198.51.100.20 "show version" --interactive-auth
```

### Validate (expected output, trimmed)

```
Interactive authentication mode enabled
Username: admin
Password: ********
Executing on 198.51.100.20: show version
Cisco IOS XE Software, Version ...
Command completed successfully
```

### Sequence example

```bash
nw run switch1 interface_status
```

Expected output (trimmed):

```
switch1: step 1/2 ... ok
switch1: step 2/2 ... ok
Sequence completed successfully
```

### Next steps

- Learn more commands → Running commands
- Store outputs → Results and Output modes
- Backups and firmware → Backups
- Credentials → Environment variables

### Troubleshooting

- Use `--interactive-auth` for ad-hoc credentials
- Verify `device_type: cisco_iosxe` for named devices (use `cisco_iosxr` for IOS-XR, `cisco_nxos` for NX-OS)
- Increase timeouts if devices are slow

## Platform identifiers

- device_type: `cisco_iosxe` (for IOS-XE and classic IOS devices)
- device_type: `cisco_iosxr` (for IOS-XR devices)
- device_type: `cisco_nxos` (for NX-OS devices)
- Platform names: Cisco IOS, Cisco IOS-XE, Cisco IOS-XR, Cisco NX-OS

**Important**: Scrapli does not have a `cisco_ios` platform. Use `cisco_iosxe` for both IOS and IOS-XE devices.

## Supported operations

- Firmware upgrade: yes (`nw upgrade`) — IOS ext: `.bin`, `.tar`; IOS-XE ext: `.bin`, `.pkg`
- Firmware downgrade: yes (`nw downgrade`) — same as upgrade workflow
- BIOS upgrade: not applicable for IOS/IOS-XE (`nw bios` not supported)
- Configuration backup: yes (`nw config-backup` or `nw backup config`)

## Firmware management

IOS (classic, monolithic image):

- Upload image to flash (SCP).
- Configure `boot system flash:<image>` after clearing existing `boot system` lines.
- Save config and `reload` with interactive confirmation.

IOS-XE INSTALL mode (preferred):

- Upload image to flash.
- `install add file flash:<image>`
- `install activate file flash:<image>` (device reloads)
- After verifying, `install commit` to make permanent; `install rollback` is available for downgrade when supported.

Networka chooses the proper workflow based on device capabilities. If INSTALL commands are not available, IOS-XE falls back to the traditional boot system method.

CLI shortcuts:

- Upgrade: `nw upgrade <device|group> <path/to/image.bin>`
- Downgrade: `nw downgrade <device|group> <path/to/older.bin>` (or `install rollback` for IOS-XE when available)

Pre-checks: by default Networka runs the `pre_maintenance` sequence before firmware actions. Override with `--precheck-sequence` or skip via `--skip-precheck`.

## Backups

- Config backup (text): `nw config-backup <device|group>`
  - Uses `show running-config` (and optionally other show commands). For Cisco, output is not saved as a remote file by default; Networka captures command output.
- Comprehensive backup: `nw backup comprehensive <device|group>`
  - Can include `show running-config`, `show startup-config`, `show version`, `show inventory`, etc.

You can define/override sequences under `config/sequences/cisco_iosxe/common.yml` (also applies to many IOS show commands). Device-specific sequences can be set per device in your config.

## Built-in command sequences

Common examples you can reference via `nw run <device> <sequence-name>`:

- `system_info`, `health_check`, `interface_status`, `network_overview`, `routing_info`, `security_audit`

See file: `config/sequences/cisco_iosxe/common.yml` for a rich set of examples that work on IOS-XE and often IOS.

## Examples

Run commands and sequences:

```bash
nw run switch1 "show version"
nw run switch1 interface_status
```

Firmware and backups:

```bash
nw upgrade switch1 ~/images/cat9k_iosxe.17.6.5.SPA.bin
nw downgrade switch1 ~/images/cat9k_iosxe.17.3.7.SPA.bin
nw config-backup switch1 --download=false
```

## Notes and tips

- Ensure there’s enough flash space before uploads; Networka doesn’t remove old images automatically.
- After IOS-XE `install activate`, use `install commit` when satisfied; `install rollback` can revert.
- Prefer SSH transport; interactive reload confirmations are handled by Networka.
