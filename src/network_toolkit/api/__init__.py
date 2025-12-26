"""Public Python API for programmatic access to Networka functionality."""

from network_toolkit.api.backup import (
    BackupOptions,
    BackupResult,
    DeviceBackupResult,
    run_backup,
)
from network_toolkit.api.diff import (
    DiffItemResult,
    DiffOptions,
    DiffOutcome,
    DiffResult,
    diff_files,
    diff_targets,
)
from network_toolkit.api.download import (
    DeviceDownloadResult,
    DownloadOptions,
    DownloadResult,
    download_file,
)
from network_toolkit.api.execution import execute_parallel
from network_toolkit.api.firmware import (
    DeviceUpgradeResult,
    FirmwareUpgradeOptions,
    FirmwareUpgradeResult,
    upgrade_firmware,
)
from network_toolkit.api.info import (
    InfoOptions,
    InfoResult,
    InfoTarget,
    get_info,
)
from network_toolkit.api.list import (
    DeviceInfo,
    GroupInfo,
    SequenceInfo,
    get_device_list,
    get_group_list,
    get_sequence_list,
)
from network_toolkit.api.routerboard_upgrade import (
    DeviceRouterboardUpgradeResult,
    RouterboardUpgradeOptions,
    RouterboardUpgradeResult,
    upgrade_routerboard,
)
from network_toolkit.api.run import (
    DeviceCommandResult,
    DeviceSequenceResult,
    RunOptions,
    RunResult,
    RunTotals,
    TargetResolution,
    TargetResolutionError,
    run_commands,
)
from network_toolkit.api.upload import (
    DeviceUploadResult,
    UploadOptions,
    UploadResult,
    upload_file,
)

__all__ = [
    # backup
    "BackupOptions",
    "BackupResult",
    "DeviceBackupResult",
    # run
    "DeviceCommandResult",
    # download
    "DeviceDownloadResult",
    # list
    "DeviceInfo",
    # routerboard
    "DeviceRouterboardUpgradeResult",
    "DeviceSequenceResult",
    # firmware
    "DeviceUpgradeResult",
    # upload
    "DeviceUploadResult",
    # diff
    "DiffItemResult",
    "DiffOptions",
    "DiffOutcome",
    "DiffResult",
    "DownloadOptions",
    "DownloadResult",
    "FirmwareUpgradeOptions",
    "FirmwareUpgradeResult",
    "GroupInfo",
    # info
    "InfoOptions",
    "InfoResult",
    "InfoTarget",
    "RouterboardUpgradeOptions",
    "RouterboardUpgradeResult",
    "RunOptions",
    "RunResult",
    "RunTotals",
    "SequenceInfo",
    "TargetResolution",
    "TargetResolutionError",
    "UploadOptions",
    "UploadResult",
    "diff_files",
    "diff_targets",
    "download_file",
    # execution
    "execute_parallel",
    "get_device_list",
    "get_group_list",
    "get_info",
    "get_sequence_list",
    "run_backup",
    "run_commands",
    "upgrade_firmware",
    "upgrade_routerboard",
    "upload_file",
]
