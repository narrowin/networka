# Platform Registry - Detailed Explanations

## Topic 1: Optional CLI Commands - What Are They?

### Current State

Right now, when you want to see what platforms are supported, you have limited options:

- Read the documentation manually
- Look at error messages when you use wrong platform
- Check `nw firmware vendors` (only shows firmware support, not everything)

### Proposed New Commands

#### Command 1: `nw platforms list`

**What it does:** Shows you ALL platforms at a glance

**Example usage:**

```bash
# Show all platforms
nw platforms list

# Show only implemented platforms
nw platforms list --status implemented

# Show only Cisco platforms
nw platforms list --vendor cisco

# Show platforms that support firmware upgrades
nw platforms list --capability firmware_upgrade
```

**Example output:**

```
Platform Support Matrix

Status: [I]=Implemented [S]=Sequences Only [P]=Planned

Platform               Vendor      Status  Firmware  Backup  Sequences
MikroTik RouterOS      MikroTik    [I]     Yes       Yes     Yes
Cisco IOS              Cisco       [I]     Yes       Yes     No
Cisco IOS-XE           Cisco       [I]     Yes       Yes     Yes
Cisco NX-OS            Cisco       [S]     No        No      Yes
Cisco IOS-XR           Cisco       [P]     No        No      No
Arista EOS             Arista      [S]     No        No      Yes
Juniper JunOS          Juniper     [S]     No        No      Yes
Nokia SR Linux         Nokia       [P]     No        No      No
Generic Linux          Linux       [P]     No        No      No
Generic Device         Generic     [P]     No        No      No

Showing 10 total platforms
3 fully implemented, 4 with sequences only, 3 planned
```

**Why this is useful:**

- Quick overview of what's supported
- Filter to find specific vendors
- See capability matrix at a glance
- Users can verify before trying to use a platform

---

#### Command 2: `nw platforms info <device_type>`

**What it does:** Shows detailed information about ONE specific platform

**Example usage:**

```bash
# Get details about MikroTik
nw platforms info mikrotik_routeros

# Get details about Cisco IOS-XE
nw platforms info cisco_iosxe
```

**Example output:**

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

Usage Examples:
  nw run device1 "show version" --platform mikrotik_routeros
  nw firmware upgrade device1 firmware.npk
  nw backup config device1
```

**Why this is useful:**

- Deep dive into one platform
- Shows exactly what operations are supported
- Shows where docs are located
- Gives usage examples
- Helps troubleshoot when something doesn't work

---

### Why These Commands Matter

**For Users:**

- Discover capabilities without reading docs
- Verify platform support before spending time on config
- Troubleshoot: "Why can't I run firmware upgrade on Cisco NX-OS?" → Check info, see it's not implemented yet

**For You (Developer):**

- Provides visibility into what's actually implemented
- Makes it obvious when docs are out of sync with code
- Users can self-serve instead of asking questions

**For Documentation:**

- Commands are self-documenting
- Always accurate (generated from registry)
- Can be used in scripts/automation

---

## Topic 2: Import Strategy - What Does "Via platforms.**init**" Mean?

### The Problem: How Should Code Import the Registry?

When you create the registry, other parts of the codebase need to import it. There are two ways to do this:

#### Option A: Direct Import (NOT Recommended)

Every file imports directly from the registry module:

```python
# In any file that needs registry
from network_toolkit.platforms.registry import PLATFORM_REGISTRY
from network_toolkit.platforms.registry import get_platform_info
from network_toolkit.platforms.registry import PlatformStatus
```

**Problems with this:**

- Exposes internal structure
- Hard to refactor later
- If you move registry.py, breaks everything
- Messy imports all over codebase

---

#### Option B: Via platforms.**init** (RECOMMENDED - YOUR CHOICE)

The `platforms/__init__.py` file re-exports registry items, creating a clean public API:

```python
# File: src/network_toolkit/platforms/__init__.py

# Import from internal modules
from network_toolkit.platforms.base import PlatformOperations
from network_toolkit.platforms.factory import get_platform_operations
from network_toolkit.platforms.registry import (
    PLATFORM_REGISTRY,
    PlatformInfo,
    PlatformStatus,
    get_platform_info,
    get_implemented_platforms,
)

# Public API - what users can import
__all__ = [
    "PlatformOperations",
    "get_platform_operations",
    "PLATFORM_REGISTRY",
    "PlatformInfo",
    "PlatformStatus",
    "get_platform_info",
    "get_implemented_platforms",
]
```

Now any file imports from the package level:

```python
# In any file that needs registry
from network_toolkit.platforms import PLATFORM_REGISTRY
from network_toolkit.platforms import get_platform_info
from network_toolkit.platforms import PlatformStatus
```

---

### Why This Matters

#### 1. Clean API Surface

Users of the platforms package don't need to know about internal structure:

**Before (messy):**

```python
from network_toolkit.platforms.registry import PLATFORM_REGISTRY
from network_toolkit.platforms.factory import get_platform_operations
from network_toolkit.platforms.base import PlatformOperations
```

**After (clean):**

```python
from network_toolkit.platforms import (
    PLATFORM_REGISTRY,
    get_platform_operations,
    PlatformOperations,
)
```

Everything comes from one place!

---

#### 2. Hides Implementation Details

If you later decide to:

- Move registry.py to a different location
- Split registry into multiple files
- Change internal structure

You only update `__init__.py`, and all other code keeps working!

**Example refactor:**

```python
# Before refactor: platforms/__init__.py
from network_toolkit.platforms.registry import PLATFORM_REGISTRY

# After refactor (split into multiple files): platforms/__init__.py
from network_toolkit.platforms.registry.core import PLATFORM_REGISTRY
from network_toolkit.platforms.registry.helpers import get_platform_info

# Code that imports still works!
from network_toolkit.platforms import PLATFORM_REGISTRY  # No change needed!
```

---

#### 3. Follows Python Best Practices

This is the "Facade Pattern" - common in Python projects:

**Real-world examples:**

```python
# requests library
from requests import get, post  # Not: from requests.api import get

# Django
from django.conf import settings  # Not: from django.conf.global_settings import settings

# Your project will do same
from network_toolkit.platforms import PLATFORM_REGISTRY
```

---

### Practical Example in Your Codebase

**Before (current code):**

```python
# File: src/network_toolkit/config.py
def get_supported_device_types() -> set[str]:
    # Hardcoded list - bad!
    return {
        "mikrotik_routeros",
        "cisco_iosxe",
        # ... 8 more
    }
```

**After (with registry, Option B import):**

```python
# File: src/network_toolkit/config.py
from network_toolkit.platforms import get_supported_device_types

# That's it! Function comes from registry
# No hardcoded list anymore
```

Or if you need more control:

```python
# File: src/network_toolkit/config.py
from network_toolkit.platforms import PLATFORM_REGISTRY

def get_supported_device_types() -> set[str]:
    """Get supported device types from registry."""
    return set(PLATFORM_REGISTRY.keys())
```

---

### Implementation Details

**Step 1: Create registry**

```python
# File: src/network_toolkit/platforms/registry.py
PLATFORM_REGISTRY = { ... }

def get_platform_info(device_type: str) -> PlatformInfo | None:
    return PLATFORM_REGISTRY.get(device_type)
```

**Step 2: Export from **init**.py**

```python
# File: src/network_toolkit/platforms/__init__.py
from network_toolkit.platforms.registry import (
    PLATFORM_REGISTRY,
    get_platform_info,
)

__all__ = [
    "PLATFORM_REGISTRY",
    "get_platform_info",
    # ... other exports
]
```

**Step 3: Use everywhere**

```python
# File: src/network_toolkit/config.py
from network_toolkit.platforms import PLATFORM_REGISTRY

# File: src/network_toolkit/commands/firmware.py
from network_toolkit.platforms import get_platform_info

# File: src/network_toolkit/commands/platforms.py
from network_toolkit.platforms import (
    PLATFORM_REGISTRY,
    get_implemented_platforms,
    PlatformStatus,
)
```

Clean, consistent, maintainable!

---

## Summary

### Optional CLI Commands

**What:** Two new commands (`nw platforms list` and `nw platforms info`) that let users discover and explore platform support

**Why:** Self-documenting, always accurate, helps users and developers understand what's supported

**Effort:** Low (2 hours), High value

---

### Import Strategy

**What:** All code imports from `network_toolkit.platforms` instead of directly from `registry.py`

**Why:** Clean API, hides internals, follows Python best practices, easy to refactor later

**How:** The `platforms/__init__.py` file re-exports everything from registry

**Benefit:** One clear import path, maintainable code structure

---

## Your Decision Recap

✅ **CLI Commands:** YES - Implement both `nw platforms list` and `nw platforms info`

✅ **Import Strategy:** YES - Use platforms.**init**.py re-export pattern

Both approved! Implementation plan has been updated with these decisions.
