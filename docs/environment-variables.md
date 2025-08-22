# Environment Variable Configuration

This document describes how to set up secure credential management using environment variables for the Networka.

## Overview

For security best practices, all device credentials have been moved from the `devices.yml` configuration file to environment variables. This prevents sensitive information from being stored in version control.

The Networka now supports multiple levels of credential management:

- **Device-specific credentials** - For individual devices
- **Group-level credentials** - For entire device groups
- **Default credentials** - Fallback for all devices

## Required Environment Variables

### Default Credentials

Set these environment variables for the default credentials used by devices that don't have specific overrides:

```bash
export NW_USER_DEFAULT=admin
export NW_PASSWORD_DEFAULT=your_secure_password_here
```

### Device-Specific Credentials (Optional)

You can override credentials for specific devices using the pattern:

- `NW_USER_DEVICENAME` - Username for the specific device
- `NW_PASSWORD_DEVICENAME` - Password for the specific device

Device names should match those in `devices.yml` and will be automatically converted to uppercase with hyphens replaced by underscores.

Examples:

```bash
# For device 'sw-acc1' in devices.yml
export NW_USER_SW_ACC1=admin
export NW_PASSWORD_SW_ACC1=switch1_password

# For device 'sw-acc2' in devices.yml
export NW_USER_SW_ACC2=admin
export NW_PASSWORD_SW_ACC2=switch2_password

# For device 'sw-dist1' in devices.yml
export NW_USER_SW_DIST1=admin
export NW_PASSWORD_SW_DIST1=distribution_password
```

### Group-Level Credentials (New Feature)

You can set credentials for entire device groups using the pattern:

- `NW_USER_GROUPNAME` - Username for all devices in the group
- `NW_PASSWORD_GROUPNAME` - Password for all devices in the group

Group names should match those in `groups.yml`:

```bash
# For group 'access_switches' in groups.yml
export NW_USER_ACCESS_SWITCHES=switch_admin
export NW_PASSWORD_ACCESS_SWITCHES=access_layer_password

# For group 'critical_infrastructure' in groups.yml
export NW_USER_CRITICAL_INFRASTRUCTURE=critical_admin
export NW_PASSWORD_CRITICAL_INFRASTRUCTURE=critical_systems_password
```

## Setup Methods

### Option 1: Environment File (.env) - Recommended

The Network Toolkit automatically loads environment variables from `.env` files, making credential management simple and secure.

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual credentials:

   ```bash
   nano .env
   ```

3. Run the tool directly - the `.env` file is loaded automatically:
   ```bash
   nw run system_info sw-acc1
   ```

#### .env File Locations

The toolkit automatically looks for `.env` files in the following order (highest to lowest precedence):

1. **Environment Variables** (Highest priority) - Variables already set in your shell
2. **Config Directory** - `.env` file in the same directory as your config files
3. **Current Working Directory** (Lowest priority) - `.env` file in your current directory

This allows for flexible credential management:

- Place `.env` in your project/config directory for project-specific credentials
- Place `.env` in your working directory for global defaults
- Use shell environment variables for runtime overrides

### Option 2: Export in Shell

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Network Toolkit Credentials
export NW_USER_DEFAULT=admin
export NW_PASSWORD_DEFAULT=your_secure_password

# Device-specific overrides
export NW_PASSWORD_SW_ACC1=switch1_password
export NW_PASSWORD_SW_ACC2=switch2_password
export NW_PASSWORD_SW_DIST1=distribution_password
```

Then reload your shell:

```bash
source ~/.bashrc
```

### Option 3: Runtime Export

Set variables directly before running commands:

```bash
export NW_USER_DEFAULT=admin
export NW_PASSWORD_DEFAULT=your_password
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

1. **Interactive credentials** (Highest) - When `--interactive-auth` is used
2. **Device configuration** - Explicitly set credentials in device YAML files (supported but discouraged)
3. **Device-specific environment variables** - `NW_USER_DEVICENAME` and `NW_PASSWORD_DEVICENAME`
4. **Group-level credentials** - From group configuration or `NW_USER_GROUPNAME` and `NW_PASSWORD_GROUPNAME`
5. **Default environment variables** (Lowest) - `NW_USER_DEFAULT` and `NW_PASSWORD_DEFAULT`

This precedence allows you to:

- Set global defaults with `NW_USER_DEFAULT` and `NW_PASSWORD_DEFAULT`
- Override entire groups with group-level credentials
- Override specific devices with device-specific credentials
- Override everything with interactive authentication

## Troubleshooting

### "Default username not found in environment"

This error means `NW_USER_DEFAULT` is not set in any of the credential sources. Set it using one of the methods above.

### "Default password not found in environment"

This error means `NW_PASSWORD_DEFAULT` is not set in any of the credential sources. Set it using one of the methods above.

### Device-specific credentials not working

Check that:

1. The environment variable name matches the device name in `devices.yml`
2. Hyphens in device names become underscores in environment variables
3. Device names are converted to uppercase for environment variables
4. The variables are exported in your current shell session
5. Use the new `NW_` prefix, not the old `NT_` prefix

### Group credentials not being applied

Check that:

1. The group name in the environment variable matches exactly the group name in `groups.yml`
2. The device is actually a member of the group (check with `nw list-groups`)
3. Use the correct format: `NW_USER_GROUPNAME` and `NW_PASSWORD_GROUPNAME`
4. Group credentials have lower priority than device-specific credentials

### Verification

You can verify your environment variables are set correctly:

```bash
# Check if default credentials are set
echo "Default user: $NW_USER_DEFAULT"
echo "Default password set: $(if [ -n "$NW_PASSWORD_DEFAULT" ]; then echo "Yes"; else echo "No"; fi)"

# Check device-specific credentials
echo "SW-ACC1 user: $NW_USER_SW_ACC1"
echo "SW-ACC1 password set: $(if [ -n "$NW_PASSWORD_SW_ACC1" ]; then echo "Yes"; else echo "No"; fi)"

# Check group credentials
echo "Access switches user: $NW_USER_ACCESS_SWITCHES"
echo "Access switches password set: $(if [ -n "$NW_PASSWORD_ACCESS_SWITCHES" ]; then echo "Yes"; else echo "No"; fi)"
```

## Migration from Old Configuration

If you have an existing `devices.yml` with hardcoded credentials:

1. Extract all `user` and `password` values from the file
2. Set them as environment variables using the patterns above
3. Remove or comment out the `user` and `password` lines from `devices.yml`
4. Test the configuration to ensure devices can still connect

The updated configuration will automatically fall back to environment variables when device-specific credentials are not found in the YAML file.
