# SPDX-License-Identifier: MIT
"""Cisco IOS-XE platform constants."""

# File extensions supported by Cisco IOS-XE
SUPPORTED_FIRMWARE_EXTENSIONS = [".bin", ".pkg"]

# Platform information
PLATFORM_NAME = "Cisco IOS-XE"
DEVICE_TYPES = ["cisco_iosxe"]

# Default backup sequence commands (example - not implemented)
DEFAULT_BACKUP_SEQUENCE = [
    "show running-config",
    "show startup-config",
]
