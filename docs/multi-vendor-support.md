# Multi-Vendor Support Documentation

## Overview

The Network Toolkit now supports multiple network vendors through a flexible, vendor-specific command sequence architecture. This allows you to manage devices from different vendors using their native command syntax while maintaining a unified interface.

## Supported Vendors

### Currently Implemented

- **MikroTik RouterOS** (`mikrotik_routeros`) - Primary focus, fully featured
- **Cisco IOS-XE** (`cisco_iosxe`) - Switches and routers
- **Cisco NX-OS** (`cisco_nxos`) - Data center switches
- **Arista EOS** (`arista_eos`) - Data center and campus switches
- **Juniper JunOS** (`juniper_junos`) - Enterprise switches and routers

### Extensibility

The architecture is designed to easily support additional vendors by:

1. Adding new vendor sequence directories
2. Creating vendor-specific command mappings
3. Updating the platform configuration

## Architecture

### Vendor-Specific Sequences

Sequences are organized by vendor platform following Scrapli naming conventions:

```
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

When executing a sequence, the toolkit follows this priority order:

1. **Global sequences** (highest priority) - Defined in `sequences.yml`
2. **Vendor-specific sequences** - Based on device's `device_type`
3. **Device-specific sequences** (lowest priority) - Defined in device configuration

### Device Configuration

Each device must specify its vendor type:

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

All vendors support these standardized sequence names with vendor-appropriate commands:

- `system_info` - Complete system information gathering
- `health_check` - Basic health monitoring
- `quick_status` - Quick device status overview
- `interface_status` - Detailed interface information
- `network_overview` - Network configuration overview
- `security_audit` - Security configuration review
- `connectivity_test` - Network connectivity testing

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
# List all sequences for all vendors
nw list sequences

# List sequences for a specific vendor
nw list sequences --vendor mikrotik_routeros

# List sequences by category
nw list sequences --category monitoring

# Verbose output with command details
nw list sequences --vendor cisco_iosxe --verbose
```

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

- `system_info`, `health_check`, `quick_status`
- `interface_status`, `network_overview`
- `security_audit`, `connectivity_test`

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

## Migration from Single-Vendor

### Existing Installations

Legacy single-file `sequences.yml` configurations are no longer supported; use modular sequences/ files.

- Gradual migration path available
- No breaking changes to existing functionality

### Migration Steps

1. Move existing sequences to `sequences/mikrotik_routeros/common.yml`
2. Update `sequences.yml` with vendor platform definitions
3. Add new vendor sequences as needed
4. Update device configurations with explicit `device_type`

## Troubleshooting

### Common Issues

#### Sequence Not Found

```
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
nw --verbose sequence device-name system_info
```

## Future Enhancements

### Planned Features

- **Dynamic sequence loading** - Load sequences based on device capabilities
- **Vendor auto-detection** - Automatically detect vendor from device responses
- **Command translation** - Translate common operations between vendor syntaxes
- **Vendor-specific drivers** - Enhanced connection handling per vendor

### Community Contributions

- Submit vendor-specific sequences
- Report vendor compatibility issues
- Contribute new vendor support
- Improve existing command mappings
