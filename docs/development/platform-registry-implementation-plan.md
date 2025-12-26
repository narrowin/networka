# Platform Registry Implementation Plan

Status: APPROVED - Ready for Implementation
Date: 2025-10-29
Branch: update-docs

## Executive Summary

This document outlines the complete implementation plan for creating a unified Platform Registry system that serves as the single source of truth for all platform/vendor information in Networka. This eliminates scattered hardcoded platform lists and ensures code and documentation stay in sync.

## Problem Statement

Currently, platform information is scattered across:

- `platforms/factory.py` - lists 3 implemented platforms
- `platforms/*/constants.py` - individual platform metadata
- `config.py` - lists 10 device types
- `builtin_sequences/` - 5 platforms with sequences
- `docs/multi-vendor-support.md` - claims 5 are "Currently Implemented" (FALSE)
- Multiple CLI commands with hardcoded lists

This leads to:

- Documentation claiming support for unimplemented platforms
- Difficult to add new platforms (update 10+ locations)
- No clear source of truth for what's actually supported

## Approved Decisions

### Decision 1: Registry Data Structure

**APPROVED: Pydantic v2 data structures (type-safe, code-only)**

- Type-safe with validation
- Modern Python best practices
- Great IDE support
- JSON schema generation capability

### Decision 2: Backward Compatibility

**APPROVED: NO backward compatibility**

- Project has no users yet
- Clean break allowed
- Remove deprecated patterns
- Simplify codebase

### Decision 3: Documentation Generation

**APPROVED: pymdownx.snippets with pre-build script**

**Rationale:**

- Already enabled in mkdocs.yml (no new dependencies)
- Follows KISS principle
- Clean separation (generate then include)
- Easy to debug and run manually
- Can integrate with pre-commit hooks

**Implementation:**

```python
# Pre-build script: scripts/generate_platform_docs.py
# In docs: --8<-- "docs/.generated/platform_support_table.md"
```

**Status Indicators:** Text-based with brackets and legend (NO EMOJIS)

- [I] = IMPLEMENTED
- [S] = SEQUENCES_ONLY
- [P] = PLANNED
- [E] = EXPERIMENTAL

### Decision 4: What to Include in Registry

**APPROVED: Include ALL platforms - even planned/experimental**

- Include: mikrotik_routeros, cisco_ios, cisco_iosxe, cisco_nxos, cisco_iosxr, arista_eos, juniper_junos, nokia_srlinux, linux, generic
- Status field: `implemented`, `sequences_only`, `planned`, `experimental`
- Clear visibility of complete roadmap
- Single source of truth for ALL device types

### Decision 5: Constants Files

**APPROVED: REMOVE constants.py files - Use registry only**

- Delete all `platforms/*/constants.py` files
- All code imports directly from registry
- No duplication of data
- Single source of truth principle

### Decision 6: Import Strategy

**APPROVED: Import via platforms.**init**.py**

- Public API: `from network_toolkit.platforms import PLATFORM_REGISTRY`
- platforms/**init**.py re-exports registry items
- Clean API surface for consumers
- Hides internal structure

### Decision 7: CLI Commands

**APPROVED: Implement new platform commands**

- `nw platforms list` - List all platforms with filtering
- `nw platforms info <device_type>` - Show detailed platform information
- Provides visibility into what's supported
- Helps users discover capabilities

## Architecture

### Registry Structure

```python
# src/network_toolkit/platforms/registry.py

from enum import Enum
from pydantic import BaseModel, Field

class PlatformStatus(str, Enum):
    IMPLEMENTED = "implemented"      # Full operations + sequences + docs
    SEQUENCES_ONLY = "sequences_only"  # Only builtin sequences, no operations
    PLANNED = "planned"              # On roadmap, no implementation
    EXPERIMENTAL = "experimental"    # Partial implementation, unstable

class PlatformCapabilities(BaseModel):
    """What operations this platform supports."""
    firmware_upgrade: bool = False
    firmware_downgrade: bool = False
    bios_upgrade: bool = False
    config_backup: bool = False
    comprehensive_backup: bool = False

class PlatformInfo(BaseModel):
    """Complete information about a network platform."""

    # Identity
    device_type: str = Field(description="Unique identifier (e.g., 'mikrotik_routeros')")
    display_name: str = Field(description="Human-readable name (e.g., 'MikroTik RouterOS')")
    vendor: str = Field(description="Vendor name (e.g., 'MikroTik')")

    # Status
    status: PlatformStatus = Field(description="Implementation status")
    description: str = Field(description="Short description for docs")

    # Technical details
    capabilities: PlatformCapabilities = Field(default_factory=PlatformCapabilities)
    firmware_extensions: list[str] = Field(default_factory=list, description="Supported firmware file extensions")

    # References
    has_operations_class: bool = Field(description="Has platform operations implementation")
    has_builtin_sequences: bool = Field(description="Has builtin command sequences")
    docs_path: str | None = Field(default=None, description="Relative path to vendor docs")
    operations_class: str | None = Field(default=None, description="Fully qualified class name")

# The single source of truth
PLATFORM_REGISTRY: dict[str, PlatformInfo] = {
    "mikrotik_routeros": PlatformInfo(
        device_type="mikrotik_routeros",
        display_name="MikroTik RouterOS",
        vendor="MikroTik",
        status=PlatformStatus.IMPLEMENTED,
        description="Primary focus, fully featured",
        capabilities=PlatformCapabilities(
            firmware_upgrade=True,
            firmware_downgrade=True,
            bios_upgrade=True,
            config_backup=True,
            comprehensive_backup=True,
        ),
        firmware_extensions=[".npk"],
        has_operations_class=True,
        has_builtin_sequences=True,
        docs_path="vendors/mikrotik/index.md",
        operations_class="network_toolkit.platforms.mikrotik_routeros.operations.MikroTikRouterOSOperations",
    ),
    "cisco_ios": PlatformInfo(
        device_type="cisco_ios",
        display_name="Cisco IOS",
        vendor="Cisco",
        status=PlatformStatus.IMPLEMENTED,
        description="Legacy Cisco switches and routers",
        capabilities=PlatformCapabilities(
            firmware_upgrade=True,
            firmware_downgrade=True,
            config_backup=True,
            comprehensive_backup=True,
        ),
        firmware_extensions=[".bin", ".tar"],
        has_operations_class=True,
        has_builtin_sequences=False,
        docs_path="vendors/cisco/index.md",
        operations_class="network_toolkit.platforms.cisco_ios.operations.CiscoIOSOperations",
    ),
    "cisco_iosxe": PlatformInfo(
        device_type="cisco_iosxe",
        display_name="Cisco IOS-XE",
        vendor="Cisco",
        status=PlatformStatus.IMPLEMENTED,
        description="Modern Cisco switches and routers",
        capabilities=PlatformCapabilities(
            firmware_upgrade=True,
            firmware_downgrade=True,
            config_backup=True,
            comprehensive_backup=True,
        ),
        firmware_extensions=[".bin", ".pkg"],
        has_operations_class=True,
        has_builtin_sequences=True,
        docs_path="vendors/cisco/index.md",
        operations_class="network_toolkit.platforms.cisco_iosxe.operations.CiscoIOSXEOperations",
    ),
    "cisco_nxos": PlatformInfo(
        device_type="cisco_nxos",
        display_name="Cisco NX-OS",
        vendor="Cisco",
        status=PlatformStatus.SEQUENCES_ONLY,
        description="Data center switches - sequences available, operations coming soon",
        has_operations_class=False,
        has_builtin_sequences=True,
        docs_path="vendors/cisco/index.md",
    ),
    "arista_eos": PlatformInfo(
        device_type="arista_eos",
        display_name="Arista EOS",
        vendor="Arista",
        status=PlatformStatus.SEQUENCES_ONLY,
        description="Data center switches - sequences available, operations coming soon",
        has_operations_class=False,
        has_builtin_sequences=True,
        docs_path="vendors/arista/index.md",
    ),
    "juniper_junos": PlatformInfo(
        device_type="juniper_junos",
        display_name="Juniper JunOS",
        vendor="Juniper",
        status=PlatformStatus.SEQUENCES_ONLY,
        description="Enterprise switches and routers - sequences available, operations coming soon",
        has_operations_class=False,
        has_builtin_sequences=True,
        docs_path="vendors/juniper/index.md",
    ),
    "nokia_srlinux": PlatformInfo(
        device_type="nokia_srlinux",
        display_name="Nokia SR Linux",
        vendor="Nokia",
        status=PlatformStatus.PLANNED,
        description="Modern data center network OS",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path="vendors/nokia/index.md",
    ),
    "cisco_iosxr": PlatformInfo(
        device_type="cisco_iosxr",
        display_name="Cisco IOS-XR",
        vendor="Cisco",
        status=PlatformStatus.PLANNED,
        description="Service provider routers",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path=None,
    ),
    "linux": PlatformInfo(
        device_type="linux",
        display_name="Generic Linux",
        vendor="Linux",
        status=PlatformStatus.PLANNED,
        description="Generic Linux hosts for scripting",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path=None,
    ),
    "generic": PlatformInfo(
        device_type="generic",
        display_name="Generic Device",
        vendor="Generic",
        status=PlatformStatus.PLANNED,
        description="Fallback for unsupported devices",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path=None,
    ),
}

# Helper functions
def get_platform_info(device_type: str) -> PlatformInfo | None:
    """Get platform info by device type."""
    return PLATFORM_REGISTRY.get(device_type)

def get_implemented_platforms() -> dict[str, PlatformInfo]:
    """Get only fully implemented platforms."""
    return {
        k: v for k, v in PLATFORM_REGISTRY.items()
        if v.status == PlatformStatus.IMPLEMENTED
    }

def get_platforms_by_status(status: PlatformStatus) -> dict[str, PlatformInfo]:
    """Get platforms by status."""
    return {
        k: v for k, v in PLATFORM_REGISTRY.items()
        if v.status == status
    }

def get_platforms_by_vendor(vendor: str) -> list[PlatformInfo]:
    """Get all platforms for a vendor."""
    return [v for v in PLATFORM_REGISTRY.values() if v.vendor.lower() == vendor.lower()]

def get_platforms_with_capability(capability: str) -> list[PlatformInfo]:
    """Get platforms supporting a specific capability."""
    return [
        v for v in PLATFORM_REGISTRY.values()
        if getattr(v.capabilities, capability, False)
    ]

def get_supported_device_types() -> set[str]:
    """Get all device types (for validation)."""
    return set(PLATFORM_REGISTRY.keys())

def validate_registry() -> list[str]:
    """Validate registry consistency. Returns list of errors."""
    errors = []

    for device_type, info in PLATFORM_REGISTRY.items():
        # Check operations class exists if claimed
        if info.has_operations_class and info.operations_class:
            # TODO: Try to import class
            pass

        # Check sequences directory exists if claimed
        if info.has_builtin_sequences:
            # TODO: Check path exists
            pass

        # Check docs exist if path specified
        if info.docs_path:
            # TODO: Check file exists
            pass

    return errors
```

## Implementation Plan

### Phase 1: Core Registry (Sprint 1 - 3 hours)

#### Task 1.1: Create registry.py

- [ ] Create `src/network_toolkit/platforms/registry.py`
- [ ] Define Pydantic models
- [ ] Populate PLATFORM_REGISTRY with all platforms
- [ ] Add helper functions
- [ ] Add validation function

**Files to create:**

- `src/network_toolkit/platforms/registry.py`

**Acceptance criteria:**

- Registry imports without errors
- All helper functions work
- Validation passes

#### Task 1.2: Create registry tests

- [ ] Create `tests/test_platform_registry.py`
- [ ] Test all helper functions
- [ ] Test validation logic
- [ ] Test Pydantic models

**Files to create:**

- `tests/test_platform_registry.py`

**Acceptance criteria:**

- 100% coverage of registry.py
- All tests pass

### Phase 2: Code Integration (Sprint 2 - 3 hours)

#### Task 2.1: Update platforms/**init**.py

- [ ] Import registry module and all public functions
- [ ] Export for public API (re-export pattern)
- [ ] Update **all** to include registry exports

**Files to modify:**

- `src/network_toolkit/platforms/__init__.py`

**Implementation:**

```python
# src/network_toolkit/platforms/__init__.py
from network_toolkit.platforms.base import PlatformOperations, UnsupportedOperationError
from network_toolkit.platforms.factory import (
    check_operation_support,
    get_platform_file_extensions,
    get_platform_operations,
    is_platform_supported,
)
from network_toolkit.platforms.registry import (
    PLATFORM_REGISTRY,
    PlatformInfo,
    PlatformStatus,
    PlatformCapabilities,
    get_platform_info,
    get_implemented_platforms,
    get_platforms_by_status,
    get_platforms_by_vendor,
    get_platforms_with_capability,
    get_supported_device_types,
    validate_registry,
)

__all__ = [
    # Base classes
    "PlatformOperations",
    "UnsupportedOperationError",
    # Factory functions (will be updated to use registry)
    "check_operation_support",
    "get_platform_file_extensions",
    "get_platform_operations",
    "is_platform_supported",
    # Registry (NEW - Single source of truth)
    "PLATFORM_REGISTRY",
    "PlatformInfo",
    "PlatformStatus",
    "PlatformCapabilities",
    "get_platform_info",
    "get_implemented_platforms",
    "get_platforms_by_status",
    "get_platforms_by_vendor",
    "get_platforms_with_capability",
    "get_supported_device_types",
    "validate_registry",
]
```

#### Task 2.2: Update factory.py

- [ ] Replace `get_supported_platforms()` with registry lookup
- [ ] Replace `is_platform_supported()` with registry lookup
- [ ] Replace `check_operation_support()` with capability check
- [ ] Replace `get_platform_file_extensions()` with registry lookup
- [ ] Delete hardcoded platform lists

**Files to modify:**

- `src/network_toolkit/platforms/factory.py`

**Lines to change:**

- Lines 65-82: Replace get_supported_platforms()
- Lines 100-108: Replace is_platform_supported()
- Lines 110-160: Replace check_operation_support()
- Lines 162-191: Replace get_platform_file_extensions()

#### Task 2.3: Update platform operations classes

- [ ] Update MikroTikRouterOSOperations.get_platform_name()
- [ ] Update MikroTikRouterOSOperations.get_device_types()
- [ ] Update MikroTikRouterOSOperations.get_supported_file_extensions()
- [ ] Same for CiscoIOSOperations
- [ ] Same for CiscoIOSXEOperations

**Files to modify:**

- `src/network_toolkit/platforms/mikrotik_routeros/operations.py`
- `src/network_toolkit/platforms/cisco_ios/operations.py`
- `src/network_toolkit/platforms/cisco_iosxe/operations.py`

**Lines to change:**

- Each file: ~3 methods near end of file

#### Task 2.4: Update config.py

- [ ] Replace `get_supported_device_types()` with registry import
- [ ] Remove hardcoded device type sets

**Files to modify:**

- `src/network_toolkit/config.py`

**Lines to change:**

- Lines 1429-1450: Replace function

#### Task 2.5: Delete platform constants files

- [ ] Delete `src/network_toolkit/platforms/mikrotik_routeros/constants.py`
- [ ] Delete `src/network_toolkit/platforms/cisco_ios/constants.py`
- [ ] Delete `src/network_toolkit/platforms/cisco_iosxe/constants.py`
- [ ] Update any imports to use registry instead
- [ ] Verify all tests still pass

**Files to delete:**

- `src/network_toolkit/platforms/mikrotik_routeros/constants.py`
- `src/network_toolkit/platforms/cisco_ios/constants.py`
- `src/network_toolkit/platforms/cisco_iosxe/constants.py`

**Rationale:** Single source of truth - all data comes from registry only

### Phase 3: Documentation Generation (Sprint 3 - 3 hours)

#### Task 3.1: Create doc generator script

- [ ] Create `scripts/generate_platform_docs.py`
- [ ] Generate platform support table
- [ ] Generate vendor overview list
- [ ] Generate capability matrix
- [ ] Write to `docs/.generated/` directory

**Files to create:**

- `scripts/generate_platform_docs.py`
- `docs/.generated/platform_support_table.md`
- `docs/.generated/platform_capabilities.md`
- `docs/.generated/vendor_list.md`

**Script should generate:**

```markdown
## Supported Platforms

| Platform          | Vendor   | Status | Firmware | Backup | Docs                                  |
| ----------------- | -------- | ------ | -------- | ------ | ------------------------------------- |
| MikroTik RouterOS | MikroTik | [I]    | Yes      | Yes    | [Guide](../vendors/mikrotik/index.md) |
| Cisco IOS         | Cisco    | [I]    | Yes      | Yes    | [Guide](../vendors/cisco/index.md)    |
| Cisco IOS-XE      | Cisco    | [I]    | Yes      | Yes    | [Guide](../vendors/cisco/index.md)    |
| Cisco NX-OS       | Cisco    | [S]    | No       | No     | [Guide](../vendors/cisco/index.md)    |
| Cisco IOS-XR      | Cisco    | [P]    | No       | No     | -                                     |
| Arista EOS        | Arista   | [S]    | No       | No     | [Guide](../vendors/arista/index.md)   |
| Juniper JunOS     | Juniper  | [S]    | No       | No     | [Guide](../vendors/juniper/index.md)  |
| Nokia SR Linux    | Nokia    | [P]    | No       | No     | [Guide](../vendors/nokia/index.md)    |
| Generic Linux     | Linux    | [P]    | No       | No     | -                                     |
| Generic Device    | Generic  | [P]    | No       | No     | -                                     |

Status Legend:

- [I] IMPLEMENTED - Full platform support with operations and sequences
- [S] SEQUENCES_ONLY - Command sequences available, operations in development
- [P] PLANNED - On roadmap, not yet implemented
- [E] EXPERIMENTAL - Partial implementation, unstable (not in use currently)
```

#### Task 3.2: Update multi-vendor-support.md

- [ ] Replace hardcoded list with snippet inclusion
- [ ] Add auto-generation notice
- [ ] Update text to reflect actual status

**Files to modify:**

- `docs/multi-vendor-support.md`

**Changes:**

```markdown
<!-- AUTO-GENERATED: Do not edit this section manually -->
<!-- Generated from src/network_toolkit/platforms/registry.py -->

--8<-- "docs/.generated/platform_support_table.md"
```

#### Task 3.3: Update vendors/index.md

- [ ] Include auto-generated vendor list
- [ ] Add status explanations
- [ ] Link to detailed guides

**Files to modify:**

- `docs/vendors/index.md`

#### Task 3.4: Add doc generation to workflow

- [ ] Update CI to run script before building docs
- [ ] Add to pre-commit hooks
- [ ] Add to Taskfile.yml as a task

**Files to modify:**

- `.github/workflows/docs.yml`
- `.pre-commit-config.yaml`
- `Taskfile.yml`

**CI Change (.github/workflows/docs.yml):**

```yaml
# Add before "Build site" step
- name: Generate platform documentation
  run: uv run python scripts/generate_platform_docs.py

- name: Build site
  run: uv run mkdocs build --strict
```

**Pre-commit Hook (.pre-commit-config.yaml):**

```yaml
# Add to local hooks
- repo: local
  hooks:
    - id: generate-platform-docs
      name: Generate platform documentation
      entry: uv run python scripts/generate_platform_docs.py
      language: system
      files: ^src/network_toolkit/platforms/registry\.py$
      pass_filenames: false
```

**Taskfile.yml:**

```yaml
generate-docs:
  desc: Generate platform documentation from registry
  cmds:
    - uv run python scripts/generate_platform_docs.py
```

### Phase 4: CLI Enhancement (Sprint 4 - 2 hours)

#### Task 4.1: Update firmware vendors command

- [ ] Use registry for display
- [ ] Show status indicators
- [ ] Color-code by implementation status

**Files to modify:**

- `src/network_toolkit/commands/firmware.py` (around line 731)

#### Task 4.2: Add platforms list command

- [ ] Create new command `nw platforms list`
- [ ] Add filters: --vendor, --status, --capability
- [ ] Rich table output with status indicators
- [ ] Register command with main CLI app

**Files to create:**

- `src/network_toolkit/commands/platforms.py`

**Expected output:**

```
Platform Support Matrix

Status: [I]=Implemented [S]=Sequences Only [P]=Planned

Platform               Vendor      Status  Firmware  Backup  Sequences
MikroTik RouterOS      MikroTik    [I]     Yes       Yes     Yes
Cisco IOS              Cisco       [I]     Yes       Yes     No
Cisco IOS-XE           Cisco       [I]     Yes       Yes     Yes
Cisco NX-OS            Cisco       [S]     No        No      Yes
Arista EOS             Arista      [S]     No        No      Yes
Juniper JunOS          Juniper     [S]     No        No      Yes

Showing 6 of 10 total platforms (use --status all to see planned platforms)
```

#### Task 4.3: Add platforms info command

- [ ] Create `nw platforms info <device_type>`
- [ ] Show detailed platform information
- [ ] Display capabilities matrix
- [ ] Show documentation link if available
- [ ] Show operations class if implemented

**Expected output:**

```
Platform: MikroTik RouterOS
Device Type: mikrotik_routeros
Vendor: MikroTik
Status: IMPLEMENTED

Description:
  Primary focus, fully featured

Capabilities:
  Firmware Upgrade: Supported
  Firmware Downgrade: Supported
  BIOS Upgrade: Supported
  Configuration Backup: Supported
  Comprehensive Backup: Supported

Technical Details:
  Operations Class: MikroTikRouterOSOperations
  Firmware Extensions: .npk
  Builtin Sequences: Yes
  Documentation: docs/vendors/mikrotik/index.md
```

### Phase 5: Testing & Validation (Sprint 5 - 2 hours)

#### Task 5.1: Integration tests

- [ ] Test factory instantiates all implemented platforms
- [ ] Test capabilities match actual methods
- [ ] Test all helper functions

**Files to create/modify:**

- `tests/integration/test_platform_registry.py`

#### Task 5.2: Validation script

- [ ] Create script to validate registry
- [ ] Check operations classes exist
- [ ] Check sequence directories exist
- [ ] Check docs exist

**Files to create:**

- `scripts/validate_platform_registry.py`

#### Task 5.3: Add validation to CI

- [ ] Run validation in CI
- [ ] Fail if registry inconsistent

**Files to modify:**

- CI configuration files

### Phase 6: Cleanup (Sprint 6 - 1 hour)

#### Task 6.1: Remove deprecated code

- [ ] Remove old hardcoded lists
- [ ] Clean up imports
- [ ] Update comments

#### Task 6.2: Update documentation

- [ ] Update development docs
- [ ] Add "how to add a platform" guide
- [ ] Update changelog

**Files to modify:**

- `docs/development.md`
- `CHANGELOG.md`

#### Task 6.3: Final review

- [ ] Check all tests pass
- [ ] Check docs build
- [ ] Check CLI commands work
- [ ] Verify no regressions

## File Changes Summary

### Files to Create (10 files)

1. `src/network_toolkit/platforms/registry.py` - Core registry with Pydantic models
2. `tests/test_platform_registry.py` - Unit tests for registry
3. `tests/integration/test_platform_registry.py` - Integration tests
4. `scripts/generate_platform_docs.py` - Documentation generator
5. `scripts/validate_platform_registry.py` - Registry validator
6. `docs/.generated/platform_support_table.md` - Auto-generated table
7. `docs/.generated/platform_capabilities.md` - Auto-generated capabilities
8. `docs/.generated/vendor_list.md` - Auto-generated vendor list
9. `docs/development/add-new-platform.md` - How-to guide
10. `src/network_toolkit/commands/platforms.py` - New CLI commands

### Files to Modify (13 files)

1. `src/network_toolkit/platforms/__init__.py` - Add registry exports
2. `src/network_toolkit/platforms/factory.py` - Use registry for all lookups
3. `src/network_toolkit/platforms/mikrotik_routeros/operations.py` - Use registry for metadata
4. `src/network_toolkit/platforms/cisco_ios/operations.py` - Use registry for metadata
5. `src/network_toolkit/platforms/cisco_iosxe/operations.py` - Use registry for metadata
6. `src/network_toolkit/config.py` - Use registry for device types
7. `docs/multi-vendor-support.md` - Include generated content via snippets
8. `docs/vendors/index.md` - Include generated vendor list
9. `src/network_toolkit/commands/firmware.py` - Use registry with text indicators
10. `.github/workflows/docs.yml` - Add doc generation step
11. `.pre-commit-config.yaml` - Add doc generation hook
12. `Taskfile.yml` - Add generate-docs task
13. `src/network_toolkit/cli.py` - Register platforms command group

### Files to Delete (3 files)

1. `src/network_toolkit/platforms/mikrotik_routeros/constants.py` - Data moved to registry
2. `src/network_toolkit/platforms/cisco_ios/constants.py` - Data moved to registry
3. `src/network_toolkit/platforms/cisco_iosxe/constants.py` - Data moved to registry

## Success Criteria

- [ ] Single source of truth for platform information exists
- [ ] All code uses registry instead of hardcoded lists
- [ ] Documentation auto-generates from registry
- [ ] Adding new platform requires updating only registry.py
- [ ] CLI commands show accurate platform status
- [ ] Tests validate registry matches reality
- [ ] Documentation clearly shows implementation status
- [ ] No breaking changes (because no users yet)
- [ ] All existing tests pass
- [ ] New tests have 100% coverage

## Timeline Estimate

- Sprint 1 (Core Registry): 3 hours
- Sprint 2 (Code Integration): 3 hours
- Sprint 3 (Documentation): 3 hours
- Sprint 4 (CLI Enhancement): 2 hours
- Sprint 5 (Testing): 2 hours
- Sprint 6 (Cleanup): 1 hour

**Total: ~14 hours** (2 working days)

## Risk Mitigation

### Risk: Registry gets out of sync

**Mitigation:**

- Automated validation in CI
- Pre-commit hooks
- Unit tests that verify consistency

### Risk: Too complex to maintain

**Mitigation:**

- KISS principle - simple Pydantic models
- Clear documentation
- Helper functions abstract complexity

### Risk: Documentation generation fails

**Mitigation:**

- Use pymdownx.snippets (already available)
- Simple script, easy to debug
- Can run manually
- Fallback to manual edit if script fails

## Next Steps

1. Review and approve this plan
2. Create feature branch: `feature/platform-registry`
3. Implement Phase 1 (Core Registry)
4. Review and test Phase 1
5. Continue with remaining phases
6. Final review and merge

## Decisions Summary

All decisions have been finalized:

1. ✅ Documentation generation: pymdownx.snippets with pre-build script
2. ✅ Status indicators: Text-based [I], [S], [P] with legend (NO EMOJIS)
3. ✅ Missing platforms: Added cisco_iosxr, linux, generic to registry
4. ✅ Constants files: DELETE them - registry is single source of truth
5. ✅ CLI commands: YES - implement `nw platforms list` and `nw platforms info`
6. ✅ Import strategy: Via platforms.**init**.py re-exports
7. ✅ Pydantic v2: Already a dependency (pydantic>=2.5.0)
8. ✅ CLI output: Text-based, no emojis, professional format

Ready for implementation!
