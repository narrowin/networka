"""Programmatic API for executing file upload operations."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

from network_toolkit.api.run import RunTotals, TargetResolution
from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.ip_device import extract_ips_from_target, is_ip_list


@dataclass(slots=True)
class UploadOptions:
    """Typed inputs for running file uploads programmatically."""

    target: str
    local_file: Path
    config: NetworkConfig
    remote_filename: str | None = None
    verify: bool = True
    checksum_verify: bool = False
    max_concurrent: int = 5
    verbose: bool = False


@dataclass(slots=True)
class DeviceUploadResult:
    """Result of an upload operation on a single device."""

    device: str
    success: bool
    local_file: Path
    remote_path: str | None = None
    error: str | None = None


@dataclass(slots=True)
class UploadResult:
    """Typed output representing an upload run."""

    target: str
    is_group: bool
    resolution: TargetResolution
    duration: float
    totals: RunTotals
    device_results: list[DeviceUploadResult] = field(default_factory=list)


def _resolve_targets(target_expr: str, config: NetworkConfig) -> TargetResolution:
    """Resolve device and group names to concrete device entries."""
    if is_ip_list(target_expr):
        ips = extract_ips_from_target(target_expr)
        return TargetResolution(
            resolved=[f"ip_{ip.replace('.', '_')}" for ip in ips],
            unknown=[],
            ip_mode=True,
        )

    requested = [t.strip() for t in target_expr.split(",") if t.strip()]
    devices: list[str] = []
    unknowns: list[str] = []

    def _add_device(name: str) -> None:
        if name not in devices:
            devices.append(name)

    for name in requested:
        if config.devices and name in config.devices:
            _add_device(name)
            continue
        if config.device_groups and name in config.device_groups:
            for member in config.get_group_members(name):
                _add_device(member)
            continue
        unknowns.append(name)

    return TargetResolution(resolved=devices, unknown=unknowns, ip_mode=False)


def _upload_single_device(
    device_name: str,
    options: UploadOptions,
) -> DeviceUploadResult:
    """Execute upload for a single device."""
    try:
        with DeviceSession(device_name, options.config) as session:
            session.connect()

            success = session.upload_file(
                local_path=options.local_file,
                remote_filename=options.remote_filename,
                verify_upload=options.verify,
                verify_checksum=options.checksum_verify,
            )

            if not success:
                return DeviceUploadResult(
                    device=device_name,
                    success=False,
                    local_file=options.local_file,
                    error="Upload failed (verification failed or other error)",
                )

            # Determine remote path (best effort guess as session.upload_file doesn't return it)
            remote_name = options.remote_filename or options.local_file.name

            return DeviceUploadResult(
                device=device_name,
                success=True,
                local_file=options.local_file,
                remote_path=remote_name,
            )

    except Exception as e:
        return DeviceUploadResult(
            device=device_name,
            success=False,
            local_file=options.local_file,
            error=str(e),
        )


def upload_file(options: UploadOptions) -> UploadResult:
    """
    Upload a file to one or more devices.

    Args:
        options: Configuration and parameters for the upload operation.

    Returns:
        UploadResult containing success/failure status for all targets.

    Raises:
        NetworkToolkitError: If target resolution fails completely or configuration is invalid.
    """
    start_time = perf_counter()

    if not options.local_file.exists():
        msg = f"Local file not found: {options.local_file}"
        raise NetworkToolkitError(msg)
    if not options.local_file.is_file():
        msg = f"Path is not a file: {options.local_file}"
        raise NetworkToolkitError(msg)

    resolution = _resolve_targets(options.target, options.config)

    if not resolution.resolved and not resolution.unknown:
        msg = "No targets specified"
        raise NetworkToolkitError(msg)

    is_group = len(resolution.resolved) > 1 or (
        options.config.device_groups and options.target in options.config.device_groups
    )

    results: list[DeviceUploadResult] = []

    # Execute uploads
    max_workers = options.max_concurrent if len(resolution.resolved) > 1 else 1

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_device = {
            executor.submit(_upload_single_device, device, options): device
            for device in resolution.resolved
        }

        for future in as_completed(future_to_device):
            results.append(future.result())

    duration = perf_counter() - start_time

    # Calculate totals
    success_count = sum(1 for r in results if r.success)
    failed_count = sum(1 for r in results if not r.success)

    totals = RunTotals(
        total=len(resolution.resolved),
        succeeded=success_count,
        failed=failed_count,
    )

    return UploadResult(
        target=options.target,
        is_group=is_group,
        resolution=resolution,
        duration=duration,
        totals=totals,
        device_results=results,
    )
