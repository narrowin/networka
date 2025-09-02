# Running commands

Common operations you'll use daily.

## Quick Demo

<div align="center">
  <img src="../assets/gifs/networka-setup.gif" alt="Networka Commands Demo" width="100%" style="max-width: 800px;"/>
  <p><em>See how to execute commands across devices and groups</em></p>
</div>

## Inspect targetsning commands

Common operations you’ll use daily.

## Inspect targets

```bash
# Device info
nw info device1
# Group info
nw info access_switches
# Sequence info
nw info health_check
```

Expected output (device):

```
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

```
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

```
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
nw download device1 config.backup
```

## Results and formatting

```bash
# Save results
nw run device1 system_info --store-results

# Choose format and target directory
nw run device1 system_info --store-results --results-format json --results-dir ./maintenance

# Adjust output styling
nw info device1 --output-mode raw
```

Notes:
- Use `--results-format json|yaml|txt` to pick a format
- Use `--results-dir <path>` to set an output directory

## Next steps

- See all flags and subcommands → CLI reference
- Store and inspect outputs → Results
- Customize CLI styling → Output modes
- Back up devices across vendors → Backups
