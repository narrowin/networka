# CSV Configuration Guide

This guide explains how to use CSV files for bulk device, group, and sequence management in Networka.

## Overview

CSV support allows you to:

- Import device inventories from spreadsheets
- Manage configurations with familiar tools (Excel, Google Sheets, etc.)
- Bulk add devices, groups, and sequences
- Mix CSV and YAML configurations seamlessly

## CSV File Headers

### Devices CSV

**Required Headers:**

- `name` - Unique device identifier
- `host` - IP address or hostname

**Optional Headers:**

- `device_type` - Device type (default: mikrotik_routeros)
- `description` - Human-readable description
- `platform` - Hardware platform
- `model` - Device model
- `location` - Physical location
- `tags` - Semicolon-separated tags

**Example:**

```csv
name,host,device_type,description,platform,model,location,tags
sw-01,192.168.1.1,mikrotik_routeros,Main Switch,mipsbe,CRS326,Rack A1,switch;core;critical
rtr-01,192.168.1.254,mikrotik_routeros,Edge Router,arm,RB4011,Network Closet,router;edge
```

### Groups CSV

**Required Headers:**

- `name` - Unique group identifier
- `description` - Human-readable description

**Optional Headers:**

- `members` - Semicolon-separated device names
- `match_tags` - Semicolon-separated tags for automatic membership

**Example:**

```csv
name,description,members,match_tags
core_switches,Core network switches,sw-01;sw-02,switch;core
edge_devices,Edge routers and firewalls,,edge;firewall
```

### Sequences CSV

**Required Headers:**

- `name` - Unique sequence identifier
- `description` - Human-readable description
- `commands` - Semicolon-separated commands

**Optional Headers:**

- `tags` - Semicolon-separated tags for categorization

**Example:**

```csv
name,description,commands,tags
health_check,Basic health check,/system/resource/print;/interface/print stats,monitoring;health
backup_config,Create backup,/export file=backup-$(date +%Y%m%d),backup;maintenance
```

## Best Practices

### Data Preparation

1. **Use consistent naming**: Device names should follow a consistent pattern
2. **Standardize tags**: Create a tag taxonomy and stick to it
3. **Validate data**: Check for typos in IP addresses and device names
4. **Use descriptions**: Always include meaningful descriptions

### Spreadsheet Tips

1. **Create templates**: Save CSV templates with headers for easy reuse
2. **Use data validation**: Set up dropdowns for device_type, platform, etc.
3. **Formula helpers**: Use formulas to generate consistent naming patterns
4. **Export considerations**: Ensure CSV exports use UTF-8 encoding

### File Organization

```
config/
├── devices/
│   ├── production.csv      # Production devices
│   ├── staging.csv         # Staging devices
│   └── lab.csv            # Lab devices
├── groups/
│   ├── infrastructure.csv  # Infrastructure groups
│   └── maintenance.csv     # Maintenance groups
└── sequences/
    ├── monitoring.csv      # Monitoring sequences
    └── operations.csv      # Operational sequences
```

## Migration Examples

### From Excel Inventory

1. **Export your device inventory** from Excel as CSV
2. **Map columns** to the required headers:
   - "Device Name" → `name`
   - "IP Address" → `host`
   - "Device Model" → `model`
   - "Location" → `location`
3. **Add missing columns** like `device_type` and `tags`
4. **Save as UTF-8 CSV** in `config/devices/inventory.csv`

### From Network Documentation

1. **Create a new spreadsheet** with the required headers
2. **Copy device information** from your documentation
3. **Add tags** based on device roles (switch, router, firewall, etc.)
4. **Export to CSV** and place in appropriate subdirectory

## Validation and Testing

### Check CSV Format

```bash
# Validate that CSV files are properly formatted
head -5 config/devices/devices.csv

# Check for common issues
grep -c "," config/devices/devices.csv  # Should match number of headers
```

### Test Loading

```bash
# Test configuration loading
nw config validate

# List devices to verify CSV loading
nw list devices

# Check specific devices from CSV
nw info device-from-csv
```

### Common Issues

1. **Extra commas**: Ensure no trailing commas in CSV lines
2. **Semicolon separators**: Use semicolons (not commas) for tags and members
3. **Missing headers**: All CSV files must have proper headers
4. **Empty names**: Device/group/sequence names cannot be empty
5. **Character encoding**: Use UTF-8 encoding for special characters

## Advanced Features

### Mixing CSV and YAML

You can use both formats together:

- **CSV for bulk data**: Device inventories, simple groups
- **YAML for complex configs**: Advanced device settings, complex sequences

### Dynamic Tag Assignment

Use formulas in spreadsheets to automatically assign tags:

```
=IF(FIND("SW",A2)>0,"switch","router")&";access"
```

### Conditional Device Configuration

Create different CSV files for different environments and load them based on your needs:

- `config/devices/production.csv`
- `config/devices/testing.csv`
- `config/devices/lab.csv`

## Troubleshooting

### CSV Not Loading

1. **Check file location**: Ensure CSV is in correct subdirectory
2. **Verify headers**: Headers must match exactly (case-sensitive)
3. **Check file encoding**: Should be UTF-8
4. **Look for warnings**: Check logs for parsing warnings

### Duplicate Devices

When using multiple CSV files, later files override earlier ones:

1. **Main devices.csv** loads first
2. **Subdirectory YAML files** load second
3. **Subdirectory CSV files** load last (highest priority)

### Tag Matching Issues

1. **Check semicolon separators**: Use `;` not `,` for multiple tags
2. **Verify tag spelling**: Tags are case-sensitive
3. **Test with simple tags**: Start with single-word tags
