# Environment Variable Configuration

This document describes how to set up secure credential management using environment variables for the Network Toolkit.

## Overview

For security best practices, all device credentials have been moved from the `devices.yml` configuration file to environment variables. This prevents sensitive information from being stored in version control.

## Required Environment Variables

### Default Credentials

Set these environment variables for the default credentials used by devices that don't have specific overrides:

```bash
export NT_DEFAULT_USER=admin
export NT_DEFAULT_PASSWORD=your_secure_password_here
```

### Device-Specific Credentials (Optional)

You can override credentials for specific devices using the pattern:
- `NT_{DEVICE_NAME}_USER` - Username for the specific device
- `NT_{DEVICE_NAME}_PASSWORD` - Password for the specific device

Device names should match those in `devices.yml` and will be automatically converted to uppercase with hyphens replaced by underscores.

Examples:
```bash
# For device 'sw-acc1' in devices.yml
export NT_SW_ACC1_USER=admin
export NT_SW_ACC1_PASSWORD=switch1_password

# For device 'sw-acc2' in devices.yml
export NT_SW_ACC2_USER=admin
export NT_SW_ACC2_PASSWORD=switch2_password

# For device 'sw-dist1' in devices.yml
export NT_SW_DIST1_USER=admin
export NT_SW_DIST1_PASSWORD=distribution_password
```

## Setup Methods

### Option 1: Environment File (.env)

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual credentials:
   ```bash
   nano .env
   ```

3. Source the environment file before running the tool:
   ```bash
   source .env
   python -m network_toolkit.cli --help
   ```

### Option 2: Export in Shell

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
# Network Toolkit Credentials
export NT_DEFAULT_USER=admin
export NT_DEFAULT_PASSWORD=your_secure_password

# Device-specific overrides
export NT_SW_ACC1_PASSWORD=switch1_password
export NT_SW_ACC2_PASSWORD=switch2_password
export NT_SW_DIST1_PASSWORD=distribution_password
```

Then reload your shell:
```bash
source ~/.bashrc
```

### Option 3: Runtime Export

Set variables directly before running commands:
```bash
export NT_DEFAULT_USER=admin
export NT_DEFAULT_PASSWORD=your_password
python -m network_toolkit.cli run system_info sw-acc1
```

## Security Best Practices

1. **Never commit `.env` files**: The `.env` file is already in `.gitignore` - keep it that way
2. **Use strong passwords**: Generate unique, complex passwords for each device
3. **Limit environment access**: Only set these variables in environments where the tool runs
4. **Regular rotation**: Change passwords regularly and update environment variables accordingly
5. **Least privilege**: Create device-specific users with minimal required permissions

## Credential Resolution Order

The toolkit resolves credentials in this priority order:

1. Device-specific environment variables (`NT_{DEVICE}_USER`, `NT_{DEVICE}_PASSWORD`)
2. Explicitly set credentials in device configuration (deprecated, not recommended)
3. Default environment variables (`NT_DEFAULT_USER`, `NT_DEFAULT_PASSWORD`)
4. If none are found, an error will be raised

## Troubleshooting

### "Default username not found in environment"

This error means `NT_DEFAULT_USER` is not set. Set it using one of the methods above.

### "Default password not found in environment"

This error means `NT_DEFAULT_PASSWORD` is not set. Set it using one of the methods above.

### Device-specific credentials not working

Check that:
1. The environment variable name matches the device name in `devices.yml`
2. Hyphens in device names become underscores in environment variables
3. Device names are converted to uppercase for environment variables
4. The variables are exported in your current shell session

### Verification

You can verify your environment variables are set correctly:
```bash
# Check if default credentials are set
echo "Default user: $NT_DEFAULT_USER"
echo "Default password set: $(if [ -n "$NT_DEFAULT_PASSWORD" ]; then echo "Yes"; else echo "No"; fi)"

# Check device-specific credentials
echo "SW-ACC1 user: $NT_SW_ACC1_USER"
echo "SW-ACC1 password set: $(if [ -n "$NT_SW_ACC1_PASSWORD" ]; then echo "Yes"; else echo "No"; fi)"
```

## Migration from Old Configuration

If you have an existing `devices.yml` with hardcoded credentials:

1. Extract all `user` and `password` values from the file
2. Set them as environment variables using the patterns above
3. Remove or comment out the `user` and `password` lines from `devices.yml`
4. Test the configuration to ensure devices can still connect

The updated configuration will automatically fall back to environment variables when device-specific credentials are not found in the YAML file.
