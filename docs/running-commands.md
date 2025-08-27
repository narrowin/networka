# Running commands

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

## Run commands

```bash
# Single command on a device
nw run device1 "/system/resource/print"

# Run on a group
nw run access_switches "show version"

# Multiple targets
nw run device1,access_switches "/system/identity/print"
```

## Run sequences

```bash
# Predefined sequence on a device
nw run device1 health_check

# On a group
nw run core_switches audit
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

## Next steps

- See all flags and subcommands → CLI reference
- Store and inspect outputs → Results
- Customize CLI styling → Output modes
- Back up devices across vendors → Backups
