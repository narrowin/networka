# Interactive Credentials Feature

## Overview

The Network Toolkit now supports interactive credential input through the `--interactive-auth` (or `-i`) flag, providing a secure way to enter credentials at runtime without storing them in environment variables or configuration files.

## Usage

Add the `--interactive-auth` or `-i` flag to any command that connects to devices:

```bash
# Device information with interactive auth
nw info sw-acc1 --interactive-auth

# Execute commands with interactive auth
nw run sw-acc1 '/system/identity/print' --interactive-auth

# Multiple devices with interactive auth (short flag)
nw run sw-acc1,sw-acc2 '/system/clock/print' -i

# Group operations with interactive auth
nw run access_switches system_info --interactive-auth
```

## Security Benefits

- **No credential storage**: Credentials exist only in memory during execution
- **Hidden password input**: Password entry is masked (not echoed to terminal)
- **Override priority**: Interactive credentials override environment variables and config files
- **Session-only**: Credentials are not saved or cached anywhere

## Implementation Details

### Core Components

1. **`src/network_toolkit/common/credentials.py`** - New module providing:
   - `InteractiveCredentials` - Type-safe credential container (NamedTuple)
   - `prompt_for_credentials()` - Secure credential input using getpass
   - `confirm_credentials()` - Optional credential verification

2. **Enhanced Configuration System** - `src/network_toolkit/config.py`:
   - `get_device_connection_params()` now accepts credential overrides
   - Maintains backward compatibility with existing credential sources

3. **Updated Device Session** - `src/network_toolkit/device.py`:
   - `DeviceSession` constructor accepts username/password overrides
   - Credential override parameters passed to connection logic

4. **CLI Integration** - Commands updated with `--interactive-auth` flag:
   - `info` command - Shows device information with interactive auth
   - `run` command - Executes commands with interactive auth support

### Credential Resolution Priority

1. **Interactive credentials** (highest priority) - When `--interactive-auth` is used
2. **Environment variables** - `NT_DEFAULT_USER`, `NT_DEFAULT_PASSWORD`, device-specific overrides
3. **Configuration file** - Default credentials in `devices.yml`

### Error Handling

- **Empty username/password**: Raises `typer.BadParameter` with descriptive message
- **KeyboardInterrupt**: Properly propagated to allow clean cancellation
- **Connection failures**: Existing error handling maintained

## Testing

### Test Coverage

- **Unit tests**: `tests/test_credentials.py` - 14 tests covering all credential functionality
- **Integration tests**: Existing CLI and config tests continue to pass
- **Validation**: All 101 existing tests pass, ensuring no regressions

### Test Categories

1. **InteractiveCredentials class**: Immutability, equality, creation
2. **Credential prompting**: Basic prompting, defaults, error conditions
3. **Credential confirmation**: Accept/reject flow, keyboard interrupts
4. **Integration scenarios**: Full workflow, rejection handling
5. **Error handling**: Exception propagation, validation

## Examples

### Basic Usage

```bash
# Info command with interactive auth
$ nw info sw-acc1 --interactive-auth
Interactive authentication mode enabled
Username [admin]: admin
Password: ********
Will use username: admin

Device: sw-acc1
├─ Connection: Not tested (use --check for live connection)
├─ Host: 192.168.1.10
├─ Port: 22
├─ Credentials: Interactive (admin)
└─ Groups: access_switches
```

### Run Command with Interactive Auth

```bash
# Execute command with interactive auth
$ nw run sw-acc1 '/system/identity/print' -i
Interactive authentication mode enabled
Username [admin]: myuser
Password: ********
Will use username: myuser

Executing on sw-acc1: /system/identity/print
name="MikroTik"
✓ Command completed successfully on sw-acc1
```

### Multiple Devices

```bash
# Run on multiple devices
$ nw run sw-acc1,sw-acc2 '/system/clock/print' --interactive-auth
Interactive authentication mode enabled
Username [admin]: admin
Password: ********
Will use username: admin

Executing on sw-acc1,sw-acc2: /system/clock/print
✓ Command completed successfully on sw-acc1
✓ Command completed successfully on sw-acc2
```

## Implementation Notes

### Type Safety

All functions use proper type annotations with Python 3.11+ typing features:

```python
def prompt_for_credentials(
    username_prompt: str = "Username",
    password_prompt: str = "Password",
    default_username: str | None = None,
) -> InteractiveCredentials:
```

### Async Compatibility

The credential system integrates seamlessly with the existing async device session architecture:

```python
# Credentials are passed as parameters to async context managers
async with DeviceSession(
    device_name,
    config,
    username_override=creds.username,
    password_override=creds.password
) as session:
    result = await session.execute_command(command)
```

### Backward Compatibility

- All existing functionality remains unchanged
- Environment variables and config files still work as before
- Interactive auth is purely additive - no breaking changes
- Existing scripts and automation continue to work

## Future Enhancements

Potential improvements for future versions:

1. **Credential caching**: Optional session-based credential caching
2. **SSH key support**: Interactive SSH key selection and passphrase entry
3. **Multi-factor auth**: Support for 2FA/MFA prompts
4. **Credential managers**: Integration with system credential stores
5. **Role-based auth**: Different credentials for different device roles

## Conclusion

The interactive credentials feature provides a secure, user-friendly way to handle authentication in the Network Toolkit while maintaining full backward compatibility and following security best practices. The implementation is well-tested, type-safe, and follows the project's architectural patterns.
