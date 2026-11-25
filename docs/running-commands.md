# Running commands

## Quick Demo

![Networka Commands Demo](assets/gifs/networka-setup.gif)

*See how to execute commands across devices and groups.*

## Inspect targets

```bash
# Device info
nw info device1
# Group info
nw info access_switches
# Sequence info
nw info system_info --device router1
```

Expected output (device):

```text
Device: device1
Host: 192.0.2.10
Port: 22
Credentials: default or interactive
Groups: access_switches
```

## Run commands

```bash
# Single command on a device
nw run device1 "/system/resource/print"

# Run on a group
nw run access_switches "show version"

# Multiple targets
nw run device1,access_switches "/system/identity/print"
```

Expected output (trimmed):

```text
Executing on device1: /system/resource/print
uptime=...
free-memory=...
Command completed successfully
```

## Run sequences

```bash
# Predefined sequence on a device
nw run device1 health_check

# On a group
nw run core_switches audit
```

Expected output (trimmed):

```text
device1: step 1/3 ... ok
device1: step 2/3 ... ok
device1: step 3/3 ... ok
Sequence completed successfully
```

## Exit status

`nw run` exits with code 0 when the command or sequence succeeded on every target device. It exits with code 1 when it failed on at least one device. This applies to a single device, a group and a device list. A group run prints the summary for all devices before it exits.

A command fails when Networka cannot connect, the login is rejected or the device rejects the command. On RouterOS, a reply that starts with `syntax error`, `bad command name`, `expected end of command`, `input does not match any value`, `failure:` or `no such item` counts as a rejected command. A sequence stops on a device at its first failed command.

## Upload and download

```bash
# Upload a file to a device
nw upload device1 firmware.npk

# Download a file from a device
nw download device1 config.backup ./config.backup
```

## Results and formatting

```bash
# Save results for a single run
nw run device1 system_info --store-results

# Override the target directory for this run (format comes from config)
nw run device1 system_info --store-results --results-dir ./maintenance

# Adjust output styling for help/readability
nw info device1 --output-mode raw
```

Notes:

- The results directory defaults to the value in `general.results_dir`; override per run with `--results-dir`.
- Choose the serialization format via `general.results_format` in `config.yml` (txt/json/yaml).

When running a command or sequence on a group or device list, `nw run` exits
with status `1` if any resolved device fails. Use the per-device outcomes and
summary to identify which devices failed.

## Next steps

- [CLI reference](reference/cli.md)
- [Save output and compare a baseline](results.md)
- [Choose an output mode](output-modes.md)
- [Back up device configuration](backups.md)
