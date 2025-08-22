# SPDX-License-Identifier: MIT
"""MikroTik RouterOS platform constants."""

# File extensions supported by RouterOS
SUPPORTED_FIRMWARE_EXTENSIONS = [".npk"]

# Platform information
PLATFORM_NAME = "MikroTik RouterOS"
DEVICE_TYPES = ["mikrotik_routeros"]

# Default backup sequence commands
DEFAULT_BACKUP_SEQUENCE = [
    "/system backup save name=nw-backup",
    "/export file=nw-export",
]

# Default download files for backup operations
DEFAULT_BACKUP_DOWNLOADS = [
    {
        "remote_file": "nw-backup.backup",
        "local_path": "{backup_dir}",
        "local_filename": "{device}_{date}_nw.backup",
        "delete_remote": False,
    },
    {
        "remote_file": "nw-export.rsc",
        "local_path": "{backup_dir}",
        "local_filename": "{device}_{date}_nw-export.rsc",
        "delete_remote": False,
    },
]
