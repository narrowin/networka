"""Public Python API for programmatic access to Networka functionality."""

from network_toolkit.api.execution import execute_parallel
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
    "execute_parallel",
    "run_commands",
]
