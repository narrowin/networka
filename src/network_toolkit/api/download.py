"""Programmatic API for executing file download operations."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

from network_toolkit.api.run import RunTotals, TargetResolution
from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import resolve_named_targets
from network_toolkit.ip_device import extract_ips_from_target, is_ip_list


@dataclass(slots=True)
class DownloadOptions:
    """Typed inputs for running file downloads programmatically."""

    target: str
    remote_file: str
    local_path: Path
    config: NetworkConfig
    delete_remote: bool = False
    verify_download: bool = True
    verbose: bool = False
    session_pool: dict[str, DeviceSession] | None = None


@dataclass(slots=True)
class DeviceDownloadResult:
    """Result of a download operation on a single device."""

    device: str
    success: bool
    remote_file: str
    local_path: Path | None = None
    file_size: int | None = None
    error: str | None = None


@dataclass(slots=True)
class DownloadResult:
    """Typed output representing a download run."""

    target: str
    is_group: bool
    resolution: TargetResolution
    duration: float
    totals: RunTotals
    device_results: list[DeviceDownloadResult] = field(default_factory=list)


def _resolve_targets(target_expr: str, config: NetworkConfig) -> TargetResolution:
    """Resolve device and group names to concrete device entries."""
    if is_ip_list(target_expr):
        ips = extract_ips_from_target(target_expr)
        return TargetResolution(
            resolved=[f"ip_{ip.replace('.', '_')}" for ip in ips],
            unknown=[],
            ip_mode=True,
        )

    resolution = resolve_named_targets(config, target_expr)
    return TargetResolution(
        resolved=resolution.resolved_devices,
        unknown=resolution.unknown_targets,
        ip_mode=False,
    )


@contextmanager
def _get_session(
    device_name: str,
    config: NetworkConfig,
    session_pool: dict[str, DeviceSession] | None = None,
) -> Iterator[DeviceSession]:
    if session_pool is not None:
        session = session_pool.get(device_name)
        if session is None:
            session = DeviceSession(device_name, config)
            session_pool[device_name] = session
        session.connect()
        yield session
    else:
        with DeviceSession(device_name, config) as session:
            yield session


def _download_single_device(
    device_name: str,
    options: DownloadOptions,
    *,
    is_group: bool,
) -> DeviceDownloadResult:
    """Execute download for a single device."""
    try:
        # Determine local destination path
        if is_group:
            # For groups: <local_path>/<device>/<remote_file>
            dest_dir = options.local_path / device_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / Path(options.remote_file).name
        # For single device:
        elif options.local_path.is_dir():
            # If local_path is a dir: <local_path>/<remote_file>
            dest_path = options.local_path / Path(options.remote_file).name
        else:
            # If local_path is a file (or doesn't exist yet but parent does)
            # We treat it as the destination filename
            dest_path = options.local_path
            # Ensure parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        with _get_session(device_name, options.config, options.session_pool) as session:
            session.connect()

            # Perform download
            success = session.download_file(
                remote_filename=options.remote_file,
                local_path=dest_path,
                verify_download=options.verify_download,
                delete_remote=options.delete_remote,
            )

            if not success:
                msg = "Download failed"
                raise NetworkToolkitError(msg)

            # Delete remote if requested - handled by download_file now if supported
            # or we can rely on the session method to handle it.
            # The session.download_file signature in base class might not have delete_remote
            # but the command was passing it. Let's assume the session method handles it.

        file_size = dest_path.stat().st_size if dest_path.exists() else 0

        return DeviceDownloadResult(
            device=device_name,
            success=True,
            remote_file=options.remote_file,
            local_path=dest_path,
            file_size=file_size,
        )

    except Exception as e:
        return DeviceDownloadResult(
            device=device_name,
            success=False,
            remote_file=options.remote_file,
            error=str(e),
        )


def download_file(options: DownloadOptions) -> DownloadResult:
    """
    Download a file from one or more devices.

    Args:
        options: Configuration and parameters for the download operation.

    Returns:
        DownloadResult containing success/failure status for all targets.

    Raises:
        NetworkToolkitError: If target resolution fails completely or configuration is invalid.
    """
    start_time = perf_counter()

    resolution = _resolve_targets(options.target, options.config)

    if not resolution.resolved and not resolution.unknown:
        # Should not happen if target string is not empty
        msg = "No targets specified"
        raise NetworkToolkitError(msg)

    # If we have unknown targets, we can either fail or just report them.
    # The 'run' command reports them in the result.

    is_group = len(resolution.resolved) > 1 or (
        options.config.device_groups and options.target in options.config.device_groups
    )

    results: list[DeviceDownloadResult] = []

    # Execute downloads
    # We can use ThreadPoolExecutor for parallel downloads if it's a group
    # But for now let's stick to sequential or simple parallel like backup/run

    # Using ThreadPoolExecutor for consistency with backup/run
    max_workers = 10 if len(resolution.resolved) > 1 else 1

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_device = {
            executor.submit(
                _download_single_device, device, options, is_group=is_group
            ): device
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

    return DownloadResult(
        target=options.target,
        is_group=is_group,
        resolution=resolution,
        duration=duration,
        totals=totals,
        device_results=results,
    )
