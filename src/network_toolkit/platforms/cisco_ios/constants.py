# SPDX-License-Identifier: MIT
"""Cisco IOS platform constants."""

# File extensions supported by Cisco IOS
SUPPORTED_FIRMWARE_EXTENSIONS = [".bin", ".tar"]

# Platform information
PLATFORM_NAME = "Cisco IOS"
DEVICE_TYPES = ["cisco_ios", "cisco_iosxe"]

# Default backup sequence commands (example - not implemented)
DEFAULT_BACKUP_SEQUENCE = [
    "show running-config",
    "show startup-config",
]
