# Scrapli Platform Expansion Implementation Plan

**Date**: October 17, 2025
**Status**: Analysis & Requirements Phase
**Goal**: Add support for all Scrapli core and community platforms

---

## Executive Summary

This document outlines the requirements, changes, and implementation strategy to expand Networka's device support from the current 3 platforms to **all 5 Scrapli core platforms** and optionally **25+ community platforms**.

**Current State**: Basic run command support works for ANY scrapli-supported platform
**Gap**: Only 3 platforms have full platform-specific operations (firmware, backups, etc.)

---

## Current Platform Support

### ✅ Fully Supported (Platform Operations Implemented)

1. **mikrotik_routeros** - MikroTik RouterOS
2. **cisco_ios** - Cisco IOS (mapped to cisco_iosxe)
3. **cisco_iosxe** - Cisco IOS-XE

### ⚠️ Partial Support (Run Commands Work, No Platform Ops)

4. **cisco_iosxr** - Cisco IOS-XR
5. **cisco_nxos** - Cisco NX-OS
6. **juniper_junos** - Juniper JunOS
7. **arista_eos** - Arista EOS
8. **linux** - Linux SSH
9. **generic** - Generic SSH

---

## Scrapli Core Platforms (Official Support)

From: https://carlmontanari.github.io/scrapli/user_guide/project_details/#supported-platforms

### Already Supported

- ✅ **cisco_iosxe** - Cisco IOS-XE (tested on: 16.12.03)
- ✅ **cisco_ios** - Cisco IOS (aliased to iosxe)

### Need Full Implementation

- 🔶 **cisco_nxos** - Cisco NX-OS (tested on: 9.2.4)
- 🔶 **cisco_iosxr** - Cisco IOS-XR (tested on: 6.5.3)
- 🔶 **juniper_junos** - Juniper JunOS (tested on: 17.3R2.10)
- 🔶 **arista_eos** - Arista EOS (tested on: 4.22.1F)

**Priority**: HIGH - These are industry-standard platforms

---

## Scrapli Community Platforms (25+ Vendors)

From: https://scrapli.github.io/scrapli_community/user_guide/project_details/#supported-platforms

### High Priority (Common Enterprise)

- **nokia_sros** - Nokia SROS
- **paloalto_panos** - PaloAlto PanOS (tested 9.x, 10.x)
- **fortinet_fortios** - Fortinet FortiOS (tested 7.0, 7.2)
- **aruba_aoscx** - Aruba AOSCX (tested 10.05.x - 10.08.x)
- **hp_comware** - HP Comware
- **huawei_vrp** - Huawei VRP

### Medium Priority (Regional/Specialized)

- **cisco_asa** - Cisco ASA (tested 9.12.x)
- **cisco_aireos** - Cisco AireOS (tested 8.5.x)
- **cisco_cbs** - Cisco CBS (Small Business)
- **vyos** - VyOS (open source router)
- **cumulus_linux** - Nvidia Cumulus Linux
- **cumulus_vtysh** - Nvidia Cumulus vtysh

### Lower Priority (Niche/Regional)

- ruckus_fastiron, ruckus_unleashed
- edgecore_ecs
- eltex_esr
- siemens_roxii
- alcatel_aos
- aethra_atosnt
- versa_flexvnf
- raisecom_ros
- dlink_os

**Note**: mikrotik_routeros exists in community but we use custom implementation

---

## Analysis: What Works TODAY?

### ✅ Run Commands Work on ALL Platforms

**Evidence from code**:

```python
# src/network_toolkit/device.py (lines 269-310)
def execute_command(self, command: str) -> str:
    """Execute a single command on the device."""
    if not self._connected or not self._transport:
        raise DeviceExecutionError(...)

    response = self._transport.send_command(command)
    return response.result
```

**This is transport-agnostic and platform-agnostic!**

The `run` command works via:

1. User specifies device_type (e.g., `arista_eos`)
2. `ConnectionParameterBuilder._map_to_scrapli_platform()` maps device_type to scrapli platform
3. `ScrapliTransportFactory` creates `Scrapli(**params)` driver
4. Scrapli automatically loads correct platform driver
5. Commands execute via transport layer

### ✅ Already Supported Device Types in Config

```python
# src/network_toolkit/config.py (lines 1429-1448)
def get_supported_device_types() -> set[str]:
    return {
        "mikrotik_routeros",
        "cisco_iosxe",
        "cisco_ios",
        "cisco_iosxr",  # ← Already accepted!
        "cisco_nxos",   # ← Already accepted!
        "juniper_junos",# ← Already accepted!
        "arista_eos",   # ← Already accepted!
        "linux",
        "generic",
    }
```

**Key Finding**: Configuration already accepts 9 device types!

### ✅ Platform Mapping Works

```python
# src/network_toolkit/credentials.py (lines 276-297)
def _map_to_scrapli_platform(self, device_type: str) -> str:
    platform_mapping = {
        "cisco_ios": "cisco_iosxe",  # Only mapping needed
    }
    return platform_mapping.get(device_type, device_type)
```

**Key Finding**: Default pass-through works for exact matches!

### 🔴 What DOESN'T Work

Only **platform-specific operations** fail:

```python
# src/network_toolkit/platforms/factory.py (lines 15-76)
def get_platform_operations(session: DeviceSession) -> PlatformOperations:
    if device_type == "mikrotik_routeros":
        return MikroTikRouterOSOperations(session)
    elif device_type == "cisco_ios":
        return CiscoIOSOperations(session)
    elif device_type == "cisco_iosxe":
        return CiscoIOSXEOperations(session)
    else:
        # ❌ FAILS HERE for juniper, arista, nxos, etc.
        raise UnsupportedOperationError(...)
```

**Operations that fail**:

- Firmware upgrades (`nw firmware upgrade`)
- BIOS upgrades
- Creating backups (platform-specific)
- Platform-specific file operations

---

## Requirements Analysis

### Requirement 1: Run Commands on All Platforms

**Status**: ✅ ALREADY WORKS

**Test Case**:

```bash
# Should work TODAY for any scrapli-supported platform
nw run 192.168.1.1 "show version" --platform arista_eos
nw run 192.168.1.2 "show version" --platform juniper_junos
nw run 192.168.1.3 "show version" --platform cisco_nxos
```

**Action Required**: NONE (verify with integration tests)

### Requirement 2: Config File Support

**Status**: ✅ MOSTLY WORKS (needs validation)

**Test Case**:

```yaml
devices:
  my_arista:
    host: 192.168.1.1
    device_type: arista_eos # Already in supported types!

  my_juniper:
    host: 192.168.1.2
    device_type: juniper_junos
```

**Action Required**: Add to validation list if not present

### Requirement 3: Platform Operations

**Status**: 🔴 NOT IMPLEMENTED

**Needed for**: firmware upgrades, backups, platform-specific features

**Action Required**: Implement `PlatformOperations` classes

### Requirement 4: Community Platform Support

**Status**: 🔴 NOT IMPLEMENTED

**Dependencies**:

- Install `scrapli_community` package
- Add device types to supported list
- Map device types to scrapli_community platform names

---

## Implementation Strategy

### Phase 1: Core Platform Support (Priority 1)

**Goal**: Full support for all 5 Scrapli core platforms

**Platforms**: cisco_nxos, cisco_iosxr, juniper_junos, arista_eos

**Files to Create**:

```
src/network_toolkit/platforms/
├── cisco_nxos/
│   ├── __init__.py
│   ├── constants.py
│   ├── operations.py
│   └── confirmation_patterns.py (if needed)
├── cisco_iosxr/
│   ├── __init__.py
│   ├── constants.py
│   └── operations.py
├── juniper_junos/
│   ├── __init__.py
│   ├── constants.py
│   └── operations.py
└── arista_eos/
    ├── __init__.py
    ├── constants.py
    └── operations.py
```

**Files to Modify**:

1. **src/network_toolkit/platforms/factory.py**

   - Add cases to `get_platform_operations()`
   - Add to `get_supported_platforms()`
   - Add to `check_operation_support()`
   - Add to `get_platform_file_extensions()`

2. **src/network_toolkit/config.py**

   - Already has device types ✅
   - Verify all are in `get_supported_device_types()`

3. **src/network_toolkit/ip_device.py**

   - Add descriptions in `get_supported_device_types()`

4. **src/network_toolkit/credentials.py**
   - Add any needed mappings to `_map_to_scrapli_platform()`

**Template for New Platform** (example: arista_eos):

```python
# src/network_toolkit/platforms/arista_eos/constants.py
PLATFORM_NAME = "Arista EOS"
DEVICE_TYPES = ["arista_eos"]
SUPPORTED_FIRMWARE_EXTENSIONS = [".swi"]  # Arista uses .swi files

# src/network_toolkit/platforms/arista_eos/operations.py
from network_toolkit.platforms.base import PlatformOperations

class AristaEOSOperations(PlatformOperations):
    @classmethod
    def get_platform_name(cls) -> str:
        return PLATFORM_NAME

    @classmethod
    def get_device_types(cls) -> list[str]:
        return DEVICE_TYPES.copy()

    @classmethod
    def get_supported_file_extensions(cls) -> list[str]:
        return SUPPORTED_FIRMWARE_EXTENSIONS.copy()

    def firmware_upgrade(self, firmware_file: Path, ...) -> dict[str, Any]:
        # Platform-specific implementation
        # Can start with NotImplementedError for MVP
        raise NotImplementedError("Arista EOS firmware upgrade not yet implemented")
```

**Effort Estimate**: 2-3 days per platform (minimal implementation)

### Phase 2: Enhanced Core Platform Support

**Goal**: Full-featured operations for core platforms

**Tasks**:

- Research firmware upgrade procedures
- Implement backup/restore operations
- Add configuration management
- Add platform-specific validation

**Effort Estimate**: 1-2 weeks per platform

### Phase 3: Community Platform Support

**Goal**: Add high-priority community platforms

**Prerequisites**:

```bash
uv add scrapli-community
```

**Files to Modify**:

1. **pyproject.toml** - Add scrapli-community dependency
2. **src/network_toolkit/config.py** - Expand `get_supported_device_types()`
3. **src/network_toolkit/credentials.py** - Add platform mappings
4. **src/network_toolkit/platforms/factory.py** - Add platform imports

**Platform Mapping Example**:

```python
def _map_to_scrapli_platform(self, device_type: str) -> str:
    platform_mapping = {
        # Core mappings
        "cisco_ios": "cisco_iosxe",

        # Community mappings
        "paloalto_panos": "paloalto_panos",  # Direct match
        "nokia_sros": "nokia_sros",
        "fortinet_fortios": "fortinet_fortios",
        # ... etc
    }
    return platform_mapping.get(device_type, device_type)
```

**Effort Estimate**: 1 day per platform (basic support)

### Phase 4: Documentation & Testing

**Documentation Needed**:

- Update platform compatibility matrix
- Add vendor-specific guides (like cisco-ios-platform-mapping.md)
- Document platform-specific quirks
- Update examples for each platform

**Testing Needed**:

- Unit tests for platform operations
- Integration tests with real devices (or vrnetlab)
- CLI tests for each platform
- Update CI/CD matrix

---

## Open Questions & Research Needed

### Q1: Firmware File Formats

**Question**: What file extensions does each platform use?

**Research Status**:

- ✅ Cisco IOS/IOS-XE: `.bin`, `.tar`, `.pkg`
- ✅ MikroTik RouterOS: `.npk`
- ❓ Cisco NX-OS: Likely `.bin`, `.rpm`, `.pkg`
- ❓ Cisco IOS-XR: Likely `.tar`, `.pie`, `.rpm`
- ❓ Juniper JunOS: Likely `.tgz`, `.tar.gz`
- ❓ Arista EOS: Likely `.swi`

**Action**: Research vendor documentation

### Q2: Firmware Upgrade Procedures

**Question**: What are the exact command sequences for upgrades?

**Research Needed**:

- Cisco NX-OS: `install all nxos bootflash:...`
- Cisco IOS-XR: `install add/activate/commit`
- Juniper JunOS: `request system software add/validate`
- Arista EOS: `copy/boot system flash:...`

**Action**: Document standard procedures per platform

### Q3: Privilege Escalation

**Question**: Do platforms require special privilege handling?

**Known**:

- ✅ MikroTik: No privilege levels
- ✅ Cisco IOS: enable mode
- ❓ NX-OS: enable mode?
- ❓ IOS-XR: admin mode?
- ❓ JunOS: operational vs configuration mode
- ❓ Arista: enable mode

**Action**: Test on real devices

### Q4: Configuration Mode Handling

**Question**: How does each platform handle configuration mode?

**Known**:

- Cisco: `configure terminal` / `end`
- JunOS: `configure` / `commit` / `exit`
- Arista: `configure` / `end`

**Action**: Implement mode detection and handling

### Q5: Backup Formats

**Question**: What format should backups use for each platform?

**Options**:

- Running config only
- Startup config
- Both configs
- Binary backup
- Text backup

**Action**: Define backup strategy per platform

### Q6: Community Platform Dependencies

**Question**: Are there version conflicts with scrapli-community?

**Test Required**:

```bash
uv add scrapli-community
# Check for dependency conflicts
```

**Action**: Test in dev environment

### Q7: Platform Detection

**Question**: Can we auto-detect platform from device responses?

**Benefit**: User doesn't need to specify platform

**Complexity**: High - would need banner/prompt parsing

**Decision**: Nice-to-have, not MVP

---

## Files Requiring Changes

### Minimal Changes (Just Add to Lists)

**High Confidence** - No breaking changes:

1. ✅ **src/network_toolkit/config.py**

   - `get_supported_device_types()` - Add new platforms to set

2. ✅ **src/network_toolkit/ip_device.py**

   - `get_supported_device_types()` - Add descriptions

3. ✅ **src/network_toolkit/credentials.py**
   - `_map_to_scrapli_platform()` - Add any needed mappings

### Moderate Changes (New Code Blocks)

**Medium Confidence** - Well-defined patterns:

4. **src/network_toolkit/platforms/factory.py**
   - `get_platform_operations()` - Add elif blocks (70 lines)
   - `get_supported_platforms()` - Add to dict (90 lines)
   - `check_operation_support()` - Add platform checks (115 lines)
   - `get_platform_file_extensions()` - Add platform checks (160 lines)

### New Files (Template-Based)

**High Confidence** - Copy existing patterns:

5. **src/network_toolkit/platforms/{platform}/**
   - `__init__.py` - Copy from cisco_ios
   - `constants.py` - Copy template, modify values
   - `operations.py` - Copy template, implement methods

### Test Files

**Standard Testing Patterns**:

6. **tests/test*platforms*{vendor}.py** - Copy existing test structure
7. **tests/test*cli_platform*{platform}.py** - CLI integration tests

### Documentation Files

8. **docs/vendors/{vendor}/index.md** - Platform guide
9. **docs/platform-compatibility.md** - Update compatibility matrix
10. **README.md** - Update supported platforms list

---

## MVP: Minimum Viable Product

### Scope: Core Platforms with Basic Support

**Platforms**: arista_eos, cisco_nxos, cisco_iosxr, juniper_junos

**Features**:

- ✅ Run commands (already works)
- ✅ Device configuration (already works)
- ✅ Platform detection in factory
- ✅ Firmware file validation
- 🔶 Firmware upgrade (stub with NotImplementedError)
- 🔶 Backup operations (stub with NotImplementedError)

**Timeline**: 1 week

**Deliverables**:

1. Platform operations stubs for 4 platforms
2. Updated factory with all mappings
3. Updated tests
4. Documentation for "basic" vs "full" support
5. Clear error messages for unimplemented operations

### Phased Rollout

**Week 1**: MVP - Basic scaffolding
**Week 2-3**: Research & implement Arista EOS fully
**Week 4-5**: Implement Cisco NX-OS fully
**Week 6-7**: Implement Juniper JunOS fully
**Week 8**: Implement Cisco IOS-XR fully
**Week 9**: Community platforms research
**Week 10**: Select & implement top 3 community platforms

---

## Testing Strategy

### Unit Tests

**For Each Platform**:

```python
class TestAristaEOSOperations:
    def test_platform_metadata(self):
        ops = AristaEOSOperations(mock_session)
        assert ops.get_platform_name() == "Arista EOS"
        assert "arista_eos" in ops.get_device_types()
        assert ".swi" in ops.get_supported_file_extensions()

    def test_firmware_upgrade_stub(self):
        ops = AristaEOSOperations(mock_session)
        with pytest.raises(NotImplementedError):
            ops.firmware_upgrade(Path("test.swi"))
```

### Integration Tests

**Test Matrix**:
| Platform | Command | Config | Upgrade | Backup |
|----------|---------|--------|---------|--------|
| arista_eos | ✅ | ✅ | 🔜 | 🔜 |
| cisco_nxos | ✅ | ✅ | 🔜 | 🔜 |
| cisco_iosxr | ✅ | ✅ | 🔜 | 🔜 |
| juniper_junos | ✅ | ✅ | 🔜 | 🔜 |

**vrnetlab Integration**:

- Set up containers for each platform
- Run functional tests against real network OS
- Validate all operations

### CLI Tests

```bash
# Test run command on each platform
pytest tests/test_cli_platform_arista.py
pytest tests/test_cli_platform_nxos.py
pytest tests/test_cli_platform_iosxr.py
pytest tests/test_cli_platform_junos.py
```

---

## Risk Assessment

### Low Risk

- ✅ Adding device types to config (non-breaking)
- ✅ Creating new platform modules (isolated)
- ✅ Adding factory cases (controlled expansion)

### Medium Risk

- ⚠️ Platform mapping changes (could affect existing platforms)
- ⚠️ Transport factory modifications (core functionality)
- ⚠️ Dependency on scrapli-community (version conflicts?)

### High Risk

- 🔴 Firmware upgrade implementation (device-breaking if wrong)
- 🔴 Breaking changes to existing platforms (backward compatibility)

**Mitigation**:

- Extensive testing before merging
- Feature flags for experimental platforms
- Clear documentation of support levels
- Rollback procedures

---

## Success Criteria

### Phase 1 Complete When:

- [ ] All 4 core platforms have PlatformOperations classes
- [ ] Factory recognizes all 4 platforms
- [ ] Run commands work on all 4 platforms
- [ ] Config accepts all 4 device types
- [ ] Tests pass for all 4 platforms
- [ ] Documentation updated

### Phase 2 Complete When:

- [ ] At least 2 platforms have full firmware upgrade
- [ ] Backup operations work on 2+ platforms
- [ ] Integration tests with real devices pass

### Phase 3 Complete When:

- [ ] scrapli-community integrated
- [ ] 3+ community platforms supported
- [ ] Documentation for community platform usage

---

## Next Steps

1. **Validate Current State** (1 day)

   - Test run commands on arista_eos, juniper_junos, cisco_nxos
   - Confirm config loading works
   - Document any current failures

2. **Research Platform Details** (2-3 days)

   - Answer all open questions
   - Document command sequences
   - Create upgrade procedure docs

3. **Implement MVP** (1 week)

   - Create platform stubs
   - Update factory
   - Add tests
   - Update docs

4. **Review & Iterate**
   - Code review
   - Test on real devices if available
   - Gather feedback
   - Plan Phase 2

---

## Appendix A: Scrapli Core Platform Details

### Cisco IOS-XE

- **Platform**: cisco_iosxe
- **Tested Version**: 16.12.03
- **Prompt**: `Router#`, `Switch#`
- **Config Mode**: `Router(config)#`

### Cisco NX-OS

- **Platform**: cisco_nxos
- **Tested Version**: 9.2.4
- **Prompt**: `switch#`
- **Config Mode**: `switch(config)#`

### Cisco IOS-XR

- **Platform**: cisco_iosxr
- **Tested Version**: 6.5.3
- **Prompt**: `RP/0/RP0/CPU0:router#`
- **Config Mode**: `RP/0/RP0/CPU0:router(config)#`

### Juniper JunOS

- **Platform**: juniper_junos
- **Tested Version**: 17.3R2.10
- **Prompt**: `user@router>`
- **Config Mode**: `[edit]`

### Arista EOS

- **Platform**: arista_eos
- **Tested Version**: 4.22.1F
- **Prompt**: `switch#`
- **Config Mode**: `switch(config)#`

---

## Appendix B: Command Reference by Platform

### Show Version Commands

- Cisco IOS/IOS-XE: `show version`
- Cisco NX-OS: `show version`
- Cisco IOS-XR: `show version`
- Juniper JunOS: `show version`
- Arista EOS: `show version`

### Configuration Commands

- Cisco IOS/IOS-XE: `show running-config`
- Cisco NX-OS: `show running-config`
- Cisco IOS-XR: `show running-config`
- Juniper JunOS: `show configuration`
- Arista EOS: `show running-config`

### Save Configuration

- Cisco IOS/IOS-XE: `copy running-config startup-config`
- Cisco NX-OS: `copy running-config startup-config`
- Cisco IOS-XR: `commit` (in config mode)
- Juniper JunOS: `commit`
- Arista EOS: `copy running-config startup-config`

---

**Document Version**: 1.0
**Last Updated**: October 17, 2025
**Status**: Ready for team review
