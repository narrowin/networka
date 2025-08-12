````instructions
# GitHub Copilot Instructions for Network Toolkit (netkit)

## Project Overview & Mission

The **Network Toolkit (netkit)** is a production-ready, async Python CLI tool for automating MikroTik RouterOS devices and other network equipment. This is **NOT a prototype** - it's a mature, fully-featured tool with 3000+ lines of well-architected code.

THE BOTH MOST IMPORTANT PRADIGMS ARE: CLARITY AND SIMPLICITY!
FOLLOW FOREMOST THE KISS PRINCIPLE: Keep It Simple, Stupid!

The software has NO USERS YET. SO DONT DO ANY BACKWARD COMPATIBILITY SHIT. KEEP MOVING FORWARD THE BEST WE CAN. LET IT RIP!

ALWAYS RUN TESTS DIRECTLY THROUGH THE VSCODE TEST FEATURE NOT THE TERMINAL! if sth is missing add it to tests instead of makeing terminal calls all the time.

Dont care about backward compatibility!

FOLLOW COMMON BEST PRACTICE DESIGN PATTERNS FOR PYTHON SOFTWARE DEVELOPMENT!!!

DONT USE EMOJIS OR ANY OTHER STUPID SYMBOLS in help, or markdown or even the Code!

### Core Mission
- **Primary focus**: MikroTik RouterOS automation with extensibility for other vendors
- **Architecture**: Modern Python 3.11+ with async/await, comprehensive type safety
- **Domain**: Network automation, device management, bulk operations, results management
- **Scale**: Handles single devices to large device groups with concurrent operations
- create production ready code
- follow the zen of python principles
- use type hints pydantic and strong typing

### Project Status
✅ **COMPLETED MILESTONES**: All major features implemented and tested
- Full CLI interface with 21+ commands
- Comprehensive device session management
- Advanced results storage and organization
- Complete bash autocompletion system
- Extensive test suite with 95%+ coverage
- Security-first credential management
- Production-ready error handling

## Architecture & Core Components

## 🔧 Technology Stack
- **CLI Framework**: Typer with Rich for beautiful output
- **Network Automation**: Scrapli with AsyncScrapli for performance
- **Data Validation**: Pydantic v2 for strict type checking
- **Package Management**: uv (modern, fast Python package manager)
- **Testing**: pytest with async support, comprehensive mocking
- **Code Quality**: Ruff (linting/formatting), mypy (type checking)

## CLI Interface & Commands

### 🚀 Primary Commands (ALL IMPLEMENTED)
```bash
# Device Information & Management
netkit info <device>                    # Show device details and connection status
netkit list-devices                     # List all configured devices
netkit list-device-groups              # Show device groups

# Command Execution
netkit run <device> <command>           # Execute single command

# Advanced Tag-Based Operations
netkit list-sequences                   # List available command sequences

# File Operations
netkit upload <device> <local> <remote>    # Upload file to device
netkit download <device> <remote> <local>    # Download file from device

# System Operations
netkit backup <device>                  # Create device backup
netkit reboot <device>                  # Reboot device with confirmation
netkit upload-firmware <device> <file> # Upload and install firmware
```

### 📊 Results Management (Comprehensive System)
```bash
# Results stored in organized structure:
results/
├── 2025-08-07_14-30-15_run_sw-acc1/
│   ├── command_context.yml           # Full command metadata
│   ├── sw-acc1_system-clock-print.txt # Command output
│   └── session_summary.yml           # Session overview
└── 2025-08-07_14-35-22_group-run_office_switches/
    ├── sw-acc1_results.txt
    ├── sw-acc2_results.txt
    └── group_summary.yml
```

## Configuration (`devices.yml`) - Enhanced Schema

The tool uses a comprehensive YAML configuration with Pydantic validation:

## Developer Workflow & Conventions

### 🛠️ Tooling & Build System
- **Package Management**: Use `uv` for all Python dependency management
- **Code Quality**: Ruff for linting/formatting, mypy for type checking
- **Testing**: pytest with async support, comprehensive mocking
- **Build**: Modern pyproject.toml with hatchling backend

### 📝 Code Style & Standards
- **Python Version**: 3.11+ (use modern typing, async patterns)
- **Type Safety**: Full type annotations, strict mypy checking
- **Docstrings**: NumPy-style with comprehensive examples
- **Error Handling**: Custom exception hierarchy with specific error types
- **Async Patterns**: Prefer async/await for all I/O operations

### 🏗️ Architecture Patterns
```python
# Proper async session management
async with DeviceSession(device_name, config) as session:
    result = await session.execute_command(command)

# Type-safe configuration handling
config = load_config(config_file)  # Returns NetworkConfig with validation

# Comprehensive error handling
try:
    result = await session.execute_command(cmd)
except DeviceConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
except DeviceExecutionError as e:
    logger.error(f"Command failed: {e}")
    raise

# Results management with context
results_manager = ResultsManager(config.general.results_dir)
results_manager.save_result(device_name, command, result, context)
```

### 🧪 Testing Patterns
```python
# Async test patterns
@pytest.mark.asyncio
async def test_device_connection(mock_config):
    with patch('scrapli.AsyncScrapli') as mock_scrapli:
        async with DeviceSession("test_device", mock_config) as session:
            result = await session.execute_command("/system/identity/print")

# Configuration fixtures
@pytest.fixture
def test_config():
    return NetworkConfig(
        general=GeneralConfig(timeout=30),
        devices={"test": DeviceConfig(host="192.168.1.1")}
    )

# Mock network operations
@patch('network_toolkit.device.AsyncScrapli')
def test_command_execution(mock_scrapli, test_config):
    # Test implementation with proper mocking
```

### 🔒 Security Best Practices
- **No Hardcoded Credentials**: All credentials via environment variables
- **Environment Variable Pattern**:
  - `NT_DEFAULT_USER`/`NT_DEFAULT_PASSWORD` for defaults
  - `NT_{DEVICE_NAME}_USER`/`NT_{DEVICE_NAME}_PASSWORD` for overrides
- **SSH Security**: Automatic host key management, secure transports only
- **Validation**: Pydantic models for all configuration validation

## Error Handling & Exception System

### 🚨 Custom Exception Hierarchy
```python
# Exception types available (from exceptions.py)
NetworkToolkitError          # Base exception for all toolkit errors
├── ConfigurationError       # Configuration file issues
├── DeviceConnectionError    # SSH connection failures
├── DeviceExecutionError     # Command execution failures
├── FileTransferError        # File upload/download issues
├── DeviceAuthError         # Authentication failures
└── DeviceTimeoutError      # Timeout-related errors
```

### 🔧 Error Handling Patterns
```python
# ✅ Preferred error handling pattern
try:
    async with DeviceSession(device_name, config) as session:
        result = await session.execute_command(command)
        return result
except DeviceConnectionError as e:
    console.print(f"[red]Failed to connect to {device_name}: {e}[/red]")
    raise
except DeviceExecutionError as e:
    console.print(f"[red]Command failed on {device_name}: {e}[/red]")
    raise
except DeviceTimeoutError as e:
    console.print(f"[yellow]Command timed out on {device_name}: {e}[/yellow]")
    raise

# ✅ Results with error context
results_manager.save_error(device_name, command, error, context)
```

## Testing Framework & Patterns

### 🧪 Test Structure
```python
# Test file organization
tests/
├── conftest.py                 # Shared fixtures and configuration
├── test_cli.py                # CLI command testing
├── test_device.py             # Device session testing
├── test_config.py             # Configuration validation
├── test_integration.py        # End-to-end integration tests
└── test_file_upload.py        # File transfer testing

# Key testing patterns
@pytest.mark.asyncio
async def test_device_connection():
    """Test async device connections with proper mocking."""

@pytest.fixture
def mock_config():
    """Provide test configuration objects."""

@patch('network_toolkit.device.Scrapli')
def test_command_execution():
    """Mock network operations for unit tests."""
```

### 🎯 Test Guidelines
- **Mock all network operations** in unit tests
- **Use pytest-asyncio** for async test functions
- **Isolate tests** with proper fixtures and teardown
- **Test error conditions** as thoroughly as success paths
- **Mock file I/O** for results management tests

## Performance & Scalability

### ⚡ Async Operation Patterns
```python
# ✅ Concurrent device operations
async def execute_on_group(group: list[str], command: str) -> dict[str, str]:
    tasks = [
        execute_on_device(device, command)
        for device in group
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(group, results))

# ✅ Connection pooling for repeated operations
class DeviceManager:
    def __init__(self):
        self._sessions: dict[str, DeviceSession] = {}

    async def get_session(self, device_name: str) -> DeviceSession:
        if device_name not in self._sessions:
            self._sessions[device_name] = DeviceSession(device_name, self.config)
        return self._sessions[device_name]
```

### 🔧 Resource Management
- **Use context managers** for all device connections
- **Implement connection pooling** for bulk operations
- **Set appropriate timeouts** for different operation types
- **Clean up resources** in finally blocks or context managers
- **Monitor memory usage** during large group operations

## Security & Best Practices

### 🔒 Credential Management
```python
# ✅ Environment variable patterns
NT_DEFAULT_USER=admin                    # Default username
NT_DEFAULT_PASSWORD=secure_password      # Default password
NT_SW_ACC1_USER=switch_admin            # Device-specific username
NT_SW_ACC1_PASSWORD=switch_password     # Device-specific password

# ✅ Credential retrieval
def get_device_credentials(device_name: str) -> tuple[str, str]:
    """Get credentials with device-specific override support."""
    user = get_env_credential(device_name, "user") or "admin"
    password = get_env_credential(device_name, "password")
    if not password:
        raise ConfigurationError(f"No password configured for {device_name}")
    return user, password
```

### 🛡️ SSH Security
- **Host key verification**: Automatic acceptance with warnings
- **Secure transport only**: No telnet fallbacks in production
- **Connection timeouts**: Prevent hanging connections
- **Credential validation**: Validate before attempting connections

## Troubleshooting & Debugging

### 🔍 Debug Modes
```bash
# Enable verbose logging
netkit --verbose run sw-acc1 "/system/clock/print"

# Check device configuration
netkit info sw-acc1

# Test connectivity
netkit run sw-acc1 "/system/identity/print"

# Validate configuration file
python -c "from network_toolkit.config import load_config; load_config('devices.yml')"
```

### 🐛 Common Issues & Solutions
1. **Connection failures**:
   - Check network connectivity: `ping <device_ip>`
   - Verify SSH access: `ssh admin@<device_ip>`
   - Check credentials: Environment variables set correctly
   - Review firewall rules: SSH port 22 accessible

2. **Authentication errors**:
   - Verify environment variables: `echo $NT_DEFAULT_USER`
   - Check device-specific overrides: `NT_{DEVICE}_USER`
   - Test manual SSH login: Confirm credentials work

3. **Command execution failures**:
   - Check RouterOS command syntax: Refer to MikroTik docs
   - Verify device permissions: User has required access
   - Test command manually: SSH and run command directly

4. **Configuration errors**:
   - Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('devices.yml'))"`
   - Check Pydantic validation: Run config loading code
   - Verify device definitions: All required fields present

### 📊 Results Analysis
```bash
# Check results directory structure
ls -la results/

# View command context
cat results/*/command_context.yml

# Check for errors
find results/ -name "*error*" -type f

# Review session summaries
find results/ -name "session_summary.yml" -exec cat {} \;
```

## Extension & Customization

### 🔌 Adding New Device Types
1. **Extend Scrapli drivers**: Add community platform support
2. **Update configuration schema**: Add device_type validation
3. **Implement device-specific handling**: Custom command formatting
4. **Add comprehensive tests**: Mock new device behavior

### 🎨 Adding New CLI Commands
```python
# Template for new CLI commands
@app.command()
def new_command(
    device: Annotated[str, typer.Argument(help="Device name")],
    config_file: Annotated[Path, typer.Option("--config", "-c")] = Path("devices.yml"),
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """
    📝 Command description with emoji and clear purpose.

    Detailed explanation of what this command does,
    including examples and usage patterns.
    """
    setup_logging("DEBUG" if verbose else "INFO")

    try:
        config = load_config(config_file)
        # Implementation here
        console.print("[green]✓[/green] Operation completed successfully")
    except NetworkToolkitError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)
```

### 📝 Adding New Output Formats
```python
# Extend ResultsManager for new formats
class ResultsManager:
    def save_result(self, device: str, command: str, result: str,
                   format: str = "txt") -> Path:
        """Save results in specified format."""
        if format == "json":
            return self._save_json(device, command, result)
        elif format == "xml":
            return self._save_xml(device, command, result)
        # Default to text format
        return self._save_text(device, command, result)
```

## MikroTik RouterOS Specifics

### 🔧 Command Syntax Patterns
```python
# Common RouterOS command patterns
SYSTEM_COMMANDS = [
    "/system/identity/print",           # Device identity
    "/system/clock/print",              # System time
    "/system/resource/print",           # System resources
    "/system/routerboard/print",        # Hardware info
]

INTERFACE_COMMANDS = [
    "/interface/print",                 # All interfaces
    "/interface/ethernet/print stats", # Ethernet statistics
    "/ip/address/print",               # IP addresses
]

ROUTING_COMMANDS = [
    "/ip/route/print",                 # Routing table
    "/routing/ospf/neighbor/print",    # OSPF neighbors
    "/routing/bgp/peer/print",         # BGP peers
]
```

### ⚠️ RouterOS Quirks & Considerations
- **Command timing**: Some commands may take longer on older hardware
- **Output formatting**: Results may vary between RouterOS versions
- **Character encoding**: Handle non-ASCII characters in device names
- **API differences**: v6 vs v7 command syntax variations
- **Resource limitations**: Older devices may have memory constraints

## References & Documentation

### 📚 Essential References
- **Scrapli Documentation**: [https://scrapli.dev](https://scrapli.dev)
  - AsyncScrapli patterns: [https://scrapli.dev/user_guide/asyncscrapli](https://scrapli.dev/user_guide/asyncscrapli)
  - Community drivers: [https://scrapli.dev/scrapli_community/](https://scrapli.dev/scrapli_community/)

- **MikroTik Documentation**:
  - SSH Reference: [https://help.mikrotik.com/docs/display/ROS/SSH](https://help.mikrotik.com/docs/display/ROS/SSH)
  - Command Reference: [https://help.mikrotik.com/docs/display/ROS/Command+Line+Interface](https://help.mikrotik.com/docs/display/ROS/Command+Line+Interface)
  - Scripting: [https://help.mikrotik.com/docs/display/ROS/Scripting](https://help.mikrotik.com/docs/display/ROS/Scripting)

- **Python Async Programming**:
  - asyncio Documentation: [https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
  - Async/Await Best Practices: [https://docs.python.org/3/library/asyncio-task.html](https://docs.python.org/3/library/asyncio-task.html)

### 🛠️ Tool-Specific Documentation
- **Typer CLI Framework**: [https://typer.tiangolo.com/](https://typer.tiangolo.com/)
- **Pydantic Data Validation**: [https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **Rich Terminal Output**: [https://rich.readthedocs.io/](https://rich.readthedocs.io/)
- **pytest Testing**: [https://pytest.org/](https://pytest.org/)
- **uv Package Manager**: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

---

## Summary for GitHub Copilot

This is a **production-ready network automation toolkit** with comprehensive features already implemented. When generating code:

1. **Follow existing patterns** from the 3000+ line codebase
2. **Use type annotations** consistently throughout
3. **Implement async/await** for all I/O operations
4. **Use custom exceptions** from the established hierarchy
5. **Include proper error handling** with user-friendly messages
6. **Test thoroughly** with mocks for network operations
7. **Document comprehensively** with NumPy-style docstrings
8. **Follow security practices** with environment variable credentials

The tool is mature, well-tested, and ready for production use. Focus on maintaining the high standards already established in the codebase.

`````
