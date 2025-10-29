# Adding Platform Support

This guide explains how to add support for new network device platforms to Networka. The platform registry architecture ensures a consistent, maintainable approach to multi-vendor support.

## Overview

Networka uses a centralized platform registry as the single source of truth for all platform information. This eliminates scattered hardcoded platform lists and ensures documentation stays automatically synchronized with code.

### Platform Status Levels

Platforms progress through implementation stages:

| Status             | Description                                      | What's Required                         |
| ------------------ | ------------------------------------------------ | --------------------------------------- |
| **PLANNED**        | On roadmap, not yet implemented                  | Registry entry only                     |
| **SEQUENCES_ONLY** | Command sequences available, no operations class | Registry + sequences                    |
| **IMPLEMENTED**    | Full operations support with all capabilities    | Registry + sequences + operations class |
| **EXPERIMENTAL**   | Partial implementation, unstable API             | Use sparingly for testing               |

## Quick Start

Adding a new platform requires updating only the platform registry. Everything else (documentation, CLI tools, validation) updates automatically.

### Minimal Addition (PLANNED Status)

Add an entry to `PLATFORM_REGISTRY` in `src/network_toolkit/platforms/registry.py`:

```python
"aruba_aoscx": PlatformInfo(
    device_type="aruba_aoscx",
    display_name="Aruba AOS-CX",
    vendor="Aruba",
    status=PlatformStatus.PLANNED,
    description="Modern Aruba data center switches",
    has_operations_class=False,
    has_builtin_sequences=False,
),
```

That's it. Run `task generate-docs` and the platform appears in all documentation automatically.

## Step-by-Step Implementation Guide

### Step 1: Add Platform to Registry

Edit `src/network_toolkit/platforms/registry.py` and add your platform to the `PLATFORM_REGISTRY` dictionary:

```python
PLATFORM_REGISTRY: dict[str, PlatformInfo] = {
    # ... existing platforms ...

    "your_platform": PlatformInfo(
        device_type="your_platform",              # Unique identifier (lowercase, underscore)
        display_name="Your Platform Name",        # Human-readable name
        vendor="VendorName",                      # Vendor name for grouping
        status=PlatformStatus.PLANNED,            # Start with PLANNED
        description="Brief platform description",
        has_operations_class=False,               # Set True when adding operations
        has_builtin_sequences=False,              # Set True when adding sequences
    ),
}
```

**Field Guidelines:**

- `device_type`: Use Scrapli naming conventions (e.g., `cisco_iosxe`, `arista_eos`)
- `display_name`: Capitalize properly (e.g., "Cisco IOS-XE", "Arista EOS")
- `vendor`: Use consistent vendor names across platforms
- `description`: One line explaining the platform's purpose or use case
- `status`: Always start with `PLANNED` and progress through stages

### Step 2: Add Command Sequences (SEQUENCES_ONLY)

If implementing sequences before full operations support:

**2a. Create sequence directory:**

```bash
mkdir -p config/sequences/your_platform
```

**2b. Create common sequences file:**

File: `config/sequences/your_platform/common.yml`

```yaml
# Common command sequences for your_platform
# Each sequence is a list of commands executed in order

system_info:
  - "show version"
  - "show system"
  - "show running-config"

interface_status:
  - "show interfaces"
  - "show interfaces status"

system_health:
  - "show environment"
  - "show memory"
  - "show cpu"
```

**Sequence Naming Conventions:**

- Use lowercase with underscores
- Use descriptive names that indicate purpose
- Prefer standardized names across platforms:
  - `system_info` - System information and version
  - `interface_status` - Interface states and statistics
  - `system_health` - CPU, memory, temperature
  - `routing_table` - Routing information
  - `arp_table` - ARP/neighbor tables

**2c. Update registry entry:**

```python
"your_platform": PlatformInfo(
    device_type="your_platform",
    display_name="Your Platform Name",
    vendor="VendorName",
    status=PlatformStatus.SEQUENCES_ONLY,  # Updated status
    description="Brief platform description",
    has_operations_class=False,
    has_builtin_sequences=True,            # Now True
),
```

Users can now run:

```bash
nw run device_name system_info
```

### Step 3: Implement Operations Class (IMPLEMENTED)

For full platform support with firmware upgrades, backups, and file transfers:

**3a. Create platform module structure:**

```bash
mkdir -p src/network_toolkit/platforms/your_platform
touch src/network_toolkit/platforms/your_platform/__init__.py
```

**3b. Create operations class:**

File: `src/network_toolkit/platforms/your_platform/operations.py`

```python
# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Operations for YourPlatform devices."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from network_toolkit.platforms.base import BaseOperations
from network_toolkit.platforms.registry import get_platform_info


class YourPlatformOperations(BaseOperations):
    """Platform operations for YourPlatform devices.

    Provides device-specific operations including:
    - Configuration backup and restore
    - Firmware upgrade management
    - File transfer operations
    """

    def __init__(self) -> None:
        """Initialize YourPlatform operations."""
        super().__init__()
        self._platform_name = "your_platform"
        self._platform_info = get_platform_info(self._platform_name)

    def get_platform_name(self) -> str:
        """Get the platform identifier."""
        return self._platform_info.display_name

    def get_device_types(self) -> list[str]:
        """Get supported device type identifiers."""
        return [self._platform_info.device_type]

    def get_supported_file_extensions(self) -> list[str]:
        """Get supported firmware file extensions."""
        return self._platform_info.firmware_extensions

    def create_backup(
        self,
        device_name: str,
        session: Any,
        backup_dir: Path,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a configuration backup for the device.

        Args:
            device_name: Name of the device
            session: Active device session
            backup_dir: Directory to store backup files
            options: Additional backup options

        Returns:
            Dictionary with backup results and file paths
        """
        # Implementation details
        pass

    def upgrade_firmware(
        self,
        session: Any,
        firmware_file: Path,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upgrade device firmware.

        Args:
            session: Active device session
            firmware_file: Path to firmware file
            options: Additional upgrade options

        Returns:
            Dictionary with upgrade results
        """
        # Implementation details
        pass

    # Add other operations as needed
```

**3c. Export from package init:**

File: `src/network_toolkit/platforms/your_platform/__init__.py`

```python
# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""YourPlatform platform support."""

from network_toolkit.platforms.your_platform.operations import (
    YourPlatformOperations,
)

__all__ = ["YourPlatformOperations"]
```

**3d. Update registry with full capabilities:**

```python
"your_platform": PlatformInfo(
    device_type="your_platform",
    display_name="Your Platform Name",
    vendor="VendorName",
    status=PlatformStatus.IMPLEMENTED,        # Fully implemented
    description="Brief platform description",
    capabilities=PlatformCapabilities(
        config_backup=True,                   # Supports config backup
        firmware_upgrade=True,                # Supports firmware upgrade
        firmware_downgrade=True,              # Supports downgrade (optional)
        bios_upgrade=False,                   # Supports BIOS upgrade (optional)
        comprehensive_backup=True,            # Full system backup
    ),
    firmware_extensions=[".bin", ".pkg"],     # Supported firmware file types
    has_operations_class=True,                # Operations class exists
    has_builtin_sequences=True,               # Sequences exist
    docs_path="vendors/yourvendor/index.md",  # Documentation path (optional)
    operations_class="network_toolkit.platforms.your_platform.operations.YourPlatformOperations",
),
```

**3e. Update platform factory (if needed):**

File: `src/network_toolkit/platforms/factory.py`

The factory should automatically discover your operations class through the registry. Verify the platform appears:

```python
from network_toolkit.platforms.factory import get_supported_platforms

platforms = get_supported_platforms()
assert "your_platform" in platforms
```

### Step 4: Create Tests

**4a. Create test file:**

File: `tests/test_platforms_your_platform.py`

```python
# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for YourPlatform operations."""

from __future__ import annotations

import pytest

from network_toolkit.platforms.registry import get_platform_info
from network_toolkit.platforms.your_platform import YourPlatformOperations


class TestYourPlatformOperations:
    """Test suite for YourPlatform operations."""

    def test_initialization(self) -> None:
        """Test operations class initializes correctly."""
        ops = YourPlatformOperations()
        assert ops is not None
        assert ops.get_platform_name() == "Your Platform Name"

    def test_device_types(self) -> None:
        """Test device type identification."""
        ops = YourPlatformOperations()
        device_types = ops.get_device_types()
        assert "your_platform" in device_types

    def test_file_extensions(self) -> None:
        """Test firmware file extension support."""
        ops = YourPlatformOperations()
        extensions = ops.get_supported_file_extensions()
        assert ".bin" in extensions

    def test_registry_entry_exists(self) -> None:
        """Test platform is registered correctly."""
        info = get_platform_info("your_platform")
        assert info is not None
        assert info.vendor == "VendorName"
        assert info.status.value == "implemented"

    # Add more tests for specific operations
    def test_create_backup(self, mocker) -> None:
        """Test backup creation."""
        # Mock session and test backup functionality
        pass

    def test_upgrade_firmware(self, mocker) -> None:
        """Test firmware upgrade."""
        # Mock session and test upgrade functionality
        pass
```

**4b. Run tests:**

```bash
# Run platform-specific tests
uv run pytest tests/test_platforms_your_platform.py -v

# Run all platform tests
uv run pytest tests/test_platform_registry.py tests/test_platforms_your_platform.py -v

# Run full test suite
uv run pytest
```

### Step 5: Generate Documentation

The documentation updates automatically:

```bash
# Generate platform documentation
task generate-docs

# Or directly
uv run python scripts/generate_platform_docs.py
```

This creates three files in `docs/.generated/`:

- `platform_support_table.md` - Status table of all platforms
- `platform_capabilities.md` - Capability matrix
- `vendor_list.md` - Vendor groupings

These are automatically included in:

- `docs/multi-vendor-support.md`
- `docs/vendors/index.md`

### Step 6: Verify Everything Works

**Check registry validation:**

```bash
uv run python -c "from network_toolkit.platforms.registry import validate_registry; print(validate_registry())"
```

**Verify CLI tools:**

```bash
# List all platforms
nw platforms list

# Check your platform
nw platforms info your_platform

# Filter by vendor
nw platforms list --vendor YourVendor

# Filter by status
nw platforms list --status implemented
```

**Test with a device:**

```bash
# Create device config
cat > ~/.config/networka/devices/test_device.yml << EOF
host: 192.168.1.1
device_type: your_platform
username: admin
password: password
EOF

# Run a sequence
nw run test_device system_info

# Run backup (if implemented)
nw backup create test_device
```

## Best Practices

### Registry Organization

**Keep entries consistent:**

- Use existing platforms as templates
- Follow Scrapli naming conventions for `device_type`
- Group related capabilities together
- Document any platform-specific quirks

### Sequence Design

**Write robust sequences:**

- Test commands on actual hardware
- Handle command variations across firmware versions
- Use commands that work in standard privilege modes
- Avoid commands requiring special licensing

**Common sequence patterns:**

```yaml
# Pattern: Information gathering
system_info:
  - "show version"
  - "show system"

# Pattern: Status checking
interface_status:
  - "show interfaces brief"
  - "show interfaces description"

# Pattern: Health monitoring
system_health:
  - "show environment"
  - "show processes cpu"
  - "show memory"
```

### Operations Implementation

**Follow the base class pattern:**

- Inherit from `BaseOperations`
- Query registry for metadata using `get_platform_info()`
- Never hardcode platform information
- Handle errors gracefully with clear messages
- Log operations at appropriate levels

**Error handling example:**

```python
def upgrade_firmware(self, session, firmware_file, options=None):
    """Upgrade device firmware."""
    if not firmware_file.exists():
        raise FileNotFoundError(f"Firmware file not found: {firmware_file}")

    ext = firmware_file.suffix.lower()
    if ext not in self.get_supported_file_extensions():
        raise ValueError(
            f"Unsupported firmware extension: {ext}. "
            f"Supported: {', '.join(self.get_supported_file_extensions())}"
        )

    # Implementation
```

### Testing Requirements

**Minimum test coverage:**

- Registry entry validation
- Operations class initialization
- Device type and extension queries
- Mock-based operation tests (backup, upgrade, etc.)
- Integration with factory pattern

**Use fixtures for common setup:**

```python
@pytest.fixture
def operations():
    """Provide operations instance."""
    return YourPlatformOperations()

@pytest.fixture
def mock_session(mocker):
    """Provide mocked device session."""
    session = mocker.MagicMock()
    session.send_command.return_value = "Mock output"
    return session
```

## Platform Status Progression

### Path 1: Sequences First (Recommended)

Start with sequences before full implementation:

1. **PLANNED** - Add registry entry

   ```python
   status=PlatformStatus.PLANNED
   ```

2. **SEQUENCES_ONLY** - Add command sequences

   ```python
   status=PlatformStatus.SEQUENCES_ONLY
   has_builtin_sequences=True
   ```

3. **IMPLEMENTED** - Add operations class
   ```python
   status=PlatformStatus.IMPLEMENTED
   has_operations_class=True
   capabilities=PlatformCapabilities(...)
   ```

### Path 2: Full Implementation

Skip directly to full implementation if you have:

- Complete understanding of platform APIs
- Test hardware available
- Time to implement and test all operations

## Troubleshooting

### Registry Validation Errors

**Error: "Status is IMPLEMENTED but operations_class is not specified"**

```python
# Fix: Add operations_class field
operations_class="network_toolkit.platforms.your_platform.operations.YourPlatformOperations"
```

**Error: "Has firmware capabilities but no firmware_extensions specified"**

```python
# Fix: Add firmware extensions
firmware_extensions=[".bin", ".pkg"]
```

### Platform Not Appearing in CLI

**Check registration:**

```bash
# Verify in Python
uv run python -c "from network_toolkit.platforms.registry import PLATFORM_REGISTRY; print('your_platform' in PLATFORM_REGISTRY)"

# Check CLI
nw platforms list | grep your_platform
```

**Common issues:**

- Typo in device_type
- Registry entry not added to dictionary
- Module import errors

### Sequences Not Found

**Verify file location:**

```bash
# Check sequence directory
ls -la config/sequences/your_platform/

# Verify YAML syntax
cat config/sequences/your_platform/common.yml
```

**Check registry flags:**

```python
has_builtin_sequences=True  # Must be True
```

### Operations Class Import Errors

**Check module structure:**

```bash
src/network_toolkit/platforms/your_platform/
├── __init__.py          # Must export operations class
└── operations.py        # Must define operations class
```

**Verify exports:**

```python
# In __init__.py
from network_toolkit.platforms.your_platform.operations import YourPlatformOperations
__all__ = ["YourPlatformOperations"]
```

## Examples

### Example 1: Simple PLANNED Platform

Minimal registry entry for future support:

```python
"paloalto_panos": PlatformInfo(
    device_type="paloalto_panos",
    display_name="Palo Alto PAN-OS",
    vendor="Palo Alto Networks",
    status=PlatformStatus.PLANNED,
    description="Next-generation firewalls",
    has_operations_class=False,
    has_builtin_sequences=False,
),
```

### Example 2: SEQUENCES_ONLY Platform

Registry entry with sequences but no operations:

```python
"fortinet_fortios": PlatformInfo(
    device_type="fortinet_fortios",
    display_name="Fortinet FortiOS",
    vendor="Fortinet",
    status=PlatformStatus.SEQUENCES_ONLY,
    description="FortiGate firewalls - sequences available",
    has_operations_class=False,
    has_builtin_sequences=True,
    docs_path="vendors/fortinet/index.md",
),
```

Sequences file at `config/sequences/fortinet_fortios/common.yml`:

```yaml
system_info:
  - "get system status"
  - "get system performance status"

interface_status:
  - "get system interface"

routing_table:
  - "get router info routing-table all"
```

### Example 3: Full IMPLEMENTED Platform

Complete registry entry with all capabilities:

```python
"aruba_aoscx": PlatformInfo(
    device_type="aruba_aoscx",
    display_name="Aruba AOS-CX",
    vendor="Aruba",
    status=PlatformStatus.IMPLEMENTED,
    description="Modern Aruba data center switches with full API support",
    capabilities=PlatformCapabilities(
        config_backup=True,
        firmware_upgrade=True,
        firmware_downgrade=False,
        bios_upgrade=False,
        comprehensive_backup=True,
    ),
    firmware_extensions=[".swi", ".bin"],
    has_operations_class=True,
    has_builtin_sequences=True,
    docs_path="vendors/aruba/index.md",
    operations_class="network_toolkit.platforms.aruba_aoscx.operations.ArubaAOSCXOperations",
),
```

## Checklist

Use this checklist when adding a new platform:

### Registry

- [ ] Added entry to `PLATFORM_REGISTRY`
- [ ] Set appropriate `status` level
- [ ] Defined `device_type` using Scrapli conventions
- [ ] Added `display_name` and `vendor`
- [ ] Wrote clear `description`
- [ ] Set `has_builtin_sequences` correctly
- [ ] Set `has_operations_class` correctly

### Sequences (if SEQUENCES_ONLY or IMPLEMENTED)

- [ ] Created directory `config/sequences/platform_name/`
- [ ] Created `common.yml` with sequences
- [ ] Tested sequences on real hardware
- [ ] Used standardized sequence names

### Operations (if IMPLEMENTED)

- [ ] Created module structure
- [ ] Implemented operations class inheriting `BaseOperations`
- [ ] Defined all required capabilities
- [ ] Added firmware extensions (if applicable)
- [ ] Exported class from `__init__.py`
- [ ] Updated `operations_class` in registry

### Testing

- [ ] Created test file `tests/test_platforms_platform_name.py`
- [ ] Added registry validation tests
- [ ] Added operations class tests
- [ ] All tests passing

### Documentation

- [ ] Ran `task generate-docs`
- [ ] Verified platform appears in generated docs
- [ ] Created vendor documentation (optional)
- [ ] Updated examples (if needed)

### Verification

- [ ] Registry validation passes
- [ ] Platform appears in `nw platforms list`
- [ ] `nw platforms info platform_name` works
- [ ] Tested with real device (if possible)
- [ ] All CI checks pass

## Resources

### Key Files

- **Registry**: `src/network_toolkit/platforms/registry.py`
- **Base class**: `src/network_toolkit/platforms/base.py`
- **Factory**: `src/network_toolkit/platforms/factory.py`
- **Doc generator**: `scripts/generate_platform_docs.py`
- **Sequences**: `config/sequences/`

### Related Documentation

- [Multi-Vendor Support](multi-vendor-support.md) - User-facing platform information
- [Development Guide](development.md) - General development workflow
- [Platform Registry Implementation](development/platform-registry-summary.md) - Architecture details

### Scrapli Platform Naming

Follow Scrapli conventions for `device_type`:

- `cisco_iosxe` - Cisco IOS-XE
- `cisco_nxos` - Cisco NX-OS
- `arista_eos` - Arista EOS
- `juniper_junos` - Juniper JunOS
- `mikrotik_routeros` - MikroTik RouterOS

See [Scrapli documentation](https://carlmontanari.github.io/scrapli/) for complete list.

## Getting Help

If you run into issues:

1. Check the troubleshooting section above
2. Validate registry with `validate_registry()`
3. Review existing platform implementations as examples
4. Check GitHub issues for similar problems
5. Create a new issue with detailed information

When reporting issues, include:

- Platform name and vendor
- Current status (PLANNED/SEQUENCES_ONLY/IMPLEMENTED)
- Error messages and stack traces
- Registry entry code
- Test results
