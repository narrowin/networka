# Multi-vendor support

## Overview

Use a logical platform to select the commands and connection behavior for a device.
Platform inspection shows the active Scrapli definition separately from
Networka's sequences and registered operations.

## CLI Commands for Platform Information

Query platform support directly from the command line:

```bash
# List active Scrapli definitions and registry entries
nw platforms list

# Filter by status
nw platforms list --status implemented
nw platforms list --status planned
nw platforms list --status sequences_only

# Filter by vendor
nw platforms list --vendor cisco
nw platforms list --vendor mikrotik

# Filter by capability
nw platforms list --capability firmware_upgrade
nw platforms list --capability config_backup

# Inspect a logical platform and its definition and sequences
nw platforms info mikrotik_routeros
nw platforms info cisco_ios
```

## Supported Vendors

The registry lists Networka's maintained operation and sequence capabilities.
Use `nw platforms list` for the broader active Scrapli catalog.

<!-- AUTO-GENERATED: Do not edit this section manually -->
<!-- Generated from src/network_toolkit/platforms/registry.py -->
<!-- Run: uv run python scripts/generate_platform_docs.py -->

--8<-- "docs/.generated/platform_support_table.md"

### Extensibility

The architecture is designed to easily support additional vendors by:

1. Adding new vendor sequence directories
2. Creating vendor-specific command mappings
3. Updating the platform configuration

## Architecture

### Vendor-Specific Sequences

Sequences use the logical `device_type`. A project can place its files in the
sequence directory next to `config.yml`:

```text
config/sequences/
├── mikrotik_routeros/
│   └── common.yml
├── cisco_iosxe/
│   └── common.yml
├── cisco_nxos/
│   └── common.yml
├── arista_eos/
│   └── common.yml
└── juniper_junos/
  └── common.yml
```

### Sequence Resolution Order

Networka uses the target's configured `device_type` to select a sequence. It searches in this order.

1. Custom user sequences in the user config directory's `sequences/custom/`.
2. User platform sequences in the user config directory's `sequences/<platform>/`.
3. Project platform sequences. Files selected in `vendor_platforms.sequence_path` and `default_files` take priority over the scan of `config/sequences/<platform>/`.
4. Packaged platform sequences.
5. `command_sequences` on the selected device.
6. Applicable global sequences from the selected configuration.

An override replaces the whole platform definition. Within a scanned directory, later filenames in sorted order win. Explicit `default_files` apply in the order written. For global sequences, `sequences:` in supplemental sequence files replace same-name definitions from `global_command_sequences:` in the main config. The loader processes root files first, then the subdirectory's named sequence file, then the remaining sibling files in filename order within each extension.

Add `device_types` to restrict a sequence to the listed logical platforms. Device-local sequences apply only to their owner. If a known name has no applicable definition for a device, Networka does not send the name as a device command.

A custom filename can start with a known platform name to scope the entire file. Otherwise, each custom definition applies to its `device_types`, or to the platforms known from defaults, configuration, and inventory when the key is omitted.

### Device Configuration

Use the logical device type in inventory, or supply it with `--platform` for
a raw IP. Scrapli loads the selected native definition. The generic `default`
definition supplies shell prompting for `linux` and `generic`. There is no
native device-platform detection.

```yaml
devices:
  mikrotik-switch:
    host: "10.0.1.10"
    device_type: "mikrotik_routeros" # Determines which sequences to use
    # ... other config

  cisco-switch:
    host: "10.0.1.20"
    device_type: "cisco_iosxe" # Uses Cisco IOS-XE sequences
    # ... other config
```

## Command Sequences

### Common Sequences Across Vendors

Maintained platforms ship sequences for common tasks. Available names and
commands vary with the logical platform and configuration. Use
`nw platforms info <platform>` to see winning sequence names and sources.

- `system_info` - Complete system information gathering
- `health_check` - Basic health monitoring
- `interface_status` - Detailed interface information
- `routing_info` - Routing-related status
- `security_audit` - Security configuration review
- `backup_config` / `backup` - Configuration and diagnostic capture

### Vendor-Specific Command Examples

#### MikroTik RouterOS

```yaml
system_info:
  commands:
    - "/system/identity/print"
    - "/system/resource/print"
    - "/system/routerboard/print"
```

#### Cisco IOS-XE

```yaml
system_info:
  commands:
    - "show version"
    - "show inventory"
    - "show environment all"
```

#### Arista EOS

```yaml
system_info:
  commands:
    - "show version"
    - "show inventory"
    - "show environment"
```

## Configuration

### Platform Configuration

The `sequences.yml` file defines vendor platform mappings:

```yaml
vendor_platforms:
  mikrotik_routeros:
    description: "MikroTik RouterOS devices"
    sequence_path: "sequences/mikrotik_routeros"
    default_files: ["common.yml"]

  cisco_iosxe:
    description: "Cisco IOS-XE devices"
    sequence_path: "sequences/cisco_iosxe"
    default_files: ["common.yml"]
```

### Device Groups by Vendor

You can create vendor-specific device groups:

```yaml
groups:
  cisco_devices:
    description: "All Cisco devices (IOS-XE and NX-OS)"
    match_tags:
      - "cisco"

  mikrotik_devices:
    description: "All MikroTik devices"
    match_tags:
      - "mikrotik"
```

## Usage Examples

### Running Vendor-Specific Sequences

```bash
# Run system_info on a MikroTik device (uses MikroTik commands)
nw run sw-mikrotik system_info

# Run system_info on a Cisco device (uses Cisco commands)
nw run sw-cisco system_info

# Run on a group with mixed vendors (automatically uses correct commands)
nw run all_switches health_check
```

### Listing Sequences by Vendor

```bash
# Browse available definitions by scope and origin
nw list sequences

# List sequences selected for a platform
nw list sequences --vendor mikrotik_routeros

# List sequences by category
nw list sequences --category monitoring

# Include source paths
nw list sequences --vendor cisco_iosxe --verbose

# Print the exact source and commands selected for a platform or device
nw info system_info --vendor cisco_iosxe
nw info system_info --device cisco-switch
```

When no default configuration is present, listing and platform inspection still show the packaged catalog and any user sequence files. A missing or invalid explicitly selected configuration is an error. Specify `--device` to inspect the exact winner for a device in inventory.

### Managing Multi-Vendor Groups

```bash
# List devices by vendor
nw list devices | grep cisco
nw list devices | grep mikrotik

# Run operations on vendor-specific groups
nw run cisco_devices health_check
nw run mikrotik_devices system_info
```

## Adding New Vendors

### Step 1: Create Vendor Directory

```bash
mkdir -p config/sequences/new_vendor
```

### Step 2: Create Sequence File

Create `config/sequences/new_vendor/common.yml`:

```yaml
sequences:
  system_info:
    description: "System information for New Vendor"
    category: "information"
    timeout: 60
    commands:
      - "show system"
      - "show version"
      # ... vendor-specific commands
```

### Step 3: Update Platform Configuration

Add to `sequences.yml`:

```yaml
vendor_platforms:
  new_vendor:
    description: "New Vendor devices"
    sequence_path: "sequences/new_vendor"
    default_files: ["common.yml"]
```

### Step 4: Configure Devices

Add devices with the new vendor type:

```yaml
devices:
  new-device:
    device_type: "new_vendor"
    # ... other configuration
```

## Best Practices

### 1. Consistent Sequence Names

Use standardized sequence names across vendors for common operations:

- `system_info`, `health_check`
- `interface_status`, `routing_info`
- `security_audit`, `backup_config`

### 2. Vendor-Specific Categories

Use consistent categories:

- `information` - Data gathering
- `monitoring` - Health checks
- `troubleshooting` - Diagnostic commands
- `security` - Security auditing

### 3. Command Timeouts

Set appropriate timeouts for different vendors:

- Some vendors may need longer timeouts for complex commands
- Consider device performance characteristics

### 4. Error Handling

Different vendors may have different:

- Command syntax variations
- Error message formats
- Connection characteristics

### 5. Testing

Always test new vendor sequences:

```bash
# Test individual commands first
nw run new-device "show version"

# Then test sequences
nw run new-device system_info
```

## Troubleshooting

### Common Issues

#### Sequence Not Found

```text
Error: Sequence 'system_info' not found for device type
```

**Solution**: Ensure the device's `device_type` matches a configured vendor platform.

#### Wrong Commands Executed

**Issue**: Device receives commands for wrong vendor
**Solution**: Verify `device_type` in device configuration matches actual device vendor.

#### Missing Vendor Sequences

**Issue**: No sequences found for vendor
**Solution**: Check that vendor sequence files exist and are properly formatted.

### Debug Commands

```bash
# Check device configuration
nw info device-name

# List available sequences for device's vendor
nw list sequences --vendor cisco_iosxe

# Test with verbose logging
nw run device-name system_info --verbose
```

## Contributing platform support

See [adding platform support](adding-platforms.md) for connection definitions,
packaged sequences, registered capabilities, and verification.
