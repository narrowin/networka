# Enhanced Configuration System Examples

This directory contains examples of the enhanced configuration system that supports:

1. **Subdirectory Organization** - All configurations in dedicated subdirectories
2. **CSV Format Support** - Define configurations using CSV files
3. **Hierarchical Loading** - Multiple files combine with override capabilities
4. **Mixed Format Support** - Use both YAML and CSV in the same project

## Directory Structure

```
config/
├── config.yml              # Main configuration (required)
├── devices/                # All device definitions here
│   ├── devices.yml         # Main devices file
│   ├── devices.csv         # CSV format devices
│   ├── production.yml      # YAML format devices
│   └── customer-a.yml      # Customer-specific devices
├── groups/                 # All group definitions here
│   ├── groups.yml          # Main groups file
│   ├── groups.csv          # CSV format groups
│   └── production.yml      # YAML format groups
├── sequences/              # All sequence definitions here
│   ├── sequences.yml       # Main sequences file
│   ├── sequences.csv       # CSV format sequences
│   └── advanced.yml        # YAML format sequences
└── examples/               # Templates and examples (this directory)
    ├── devices/
    ├── groups/
    └── sequences/
```

## CSV Format Reference

### Devices CSV Format
**Headers**: `name,host,device_type,description,platform,model,location,tags`

- **name**: Unique device identifier (required)
- **host**: IP address or hostname (required)
- **device_type**: Device type (default: mikrotik_routeros)
- **description**: Human-readable description
- **platform**: Hardware platform
- **model**: Device model
- **location**: Physical location
- **tags**: Semicolon-separated tags (e.g., "switch;access;lab")

### Groups CSV Format
**Headers**: `name,description,members,match_tags`

- **name**: Unique group identifier (required)
- **description**: Human-readable description (required)
- **members**: Semicolon-separated device names
- **match_tags**: Semicolon-separated tags for automatic membership

### Sequences CSV Format
**Headers**: `name,description,commands,tags`

- **name**: Unique sequence identifier (required)
- **description**: Human-readable description (required)
- **commands**: Semicolon-separated commands (required)
- **tags**: Semicolon-separated tags for categorization

## Loading Priority

Configuration files are loaded from their respective subdirectories and combined:

1. **All device files**: `config/devices/*.{yml,yaml,csv}` (alphabetical order)
2. **All group files**: `config/groups/*.{yml,yaml,csv}` (alphabetical order)
3. **All sequence files**: `config/sequences/*.{yml,yaml,csv}` (alphabetical order)

Files loaded later can override configurations from earlier files.

## Use Cases

### 1. Customer Separation
```
config/devices/
├── customer-a.yml
├── customer-b.yml
└── shared-infrastructure.yml
```

### 2. Environment Separation
```
config/devices/
├── production.yml
├── staging.yml
└── development.csv
```

### 3. Bulk Import from Spreadsheets
Convert your device inventory spreadsheets to CSV format and place them in the appropriate subdirectories.

### 4. Mixed Teams
- Network engineers can use YAML for complex configurations
- Operations teams can use CSV for simple bulk additions
- Both formats work together seamlessly

## Migration Guide

### Setting Up New Configuration

1. **Copy examples**: Start with templates from this examples directory
2. **Create your configs**: Place files in the appropriate subdirectories:
   - Device configs → `config/devices/`
   - Group configs → `config/groups/`
   - Sequence configs → `config/sequences/`
3. **Use appropriate format**: YAML for complex configs, CSV for bulk data

### Converting From Legacy Single Files

If you have existing `devices.yml`, `groups.yml`, `sequences.yml` files:

1. **Move device configs**: `devices.yml` → `config/devices/devices.yml`
2. **Move group configs**: `groups.yml` → `config/groups/groups.yml`
3. **Move sequence configs**: `sequences.yml` → `config/sequences/sequences.yml`
4. **Split general config**: Extract `general:` section to `config/config.yml`

## Best Practices

1. **Use descriptive filenames** in subdirectories
2. **Maintain consistent tagging** across all formats
3. **Document complex configurations** in YAML format
4. **Use CSV for bulk operations** and simple definitions
5. **Test configurations** after adding new files
