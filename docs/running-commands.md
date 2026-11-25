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

A group run can exit successfully while some targets report failures. Check
the per-device outcomes and summary when using a group run for verification.

## Next steps

- [CLI reference](reference/cli.md)
- [Save output and compare a baseline](results.md)
- [Choose an output mode](output-modes.md)
- [Back up device configuration](backups.md)
