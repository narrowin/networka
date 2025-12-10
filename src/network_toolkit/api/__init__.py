"""Public Python API for programmatic access to Networka functionality."""

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

__all__ = [
    "DeviceCommandResult",
    "DeviceSequenceResult",
    "RunOptions",
    "RunResult",
    "RunTotals",
    "TargetResolution",
    "TargetResolutionError",
    "run_commands",
]
