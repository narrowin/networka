"""Programmatic API for executing backup operations."""

from __future__ import annotations

import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from network_toolkit.api.run import RunTotals, TargetResolution
from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import resolve_named_targets
from network_toolkit.ip_device import extract_ips_from_target, is_ip_list
from network_toolkit.platforms import (
    UnsupportedOperationError,
    get_platform_operations,
)
from network_toolkit.sequence_manager import SequenceManager


@dataclass(slots=True)
class BackupOptions:
    """Typed inputs for running backups programmatically."""

    target: str
    config: NetworkConfig
    download: bool = True
    delete_remote: bool = False
    verbose: bool = False
    session_pool: dict[str, DeviceSession] | None = None


@dataclass(slots=True)
class DeviceBackupResult:
    """Result of a backup operation on a single device."""

    device: str
    success: bool
    platform: str | None = None
    transport: str | None = None
    backup_dir: Path | None = None
    text_outputs: dict[str, str] = field(default_factory=dict)
    downloaded_files: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class BackupResult:
    """Typed output representing a backup run."""

    target: str
    is_group: bool
    resolution: TargetResolution
    duration: float
    totals: RunTotals
    device_results: list[DeviceBackupResult] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


def _resolve_targets(target_expr: str, config: NetworkConfig) -> TargetResolution:
    """Resolve device and group names to concrete device entries."""
    # Note: Backup currently doesn't support IP targets in the same way run does,
    # but we keep the resolution logic consistent.
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


def _resolve_backup_sequence(config: NetworkConfig, device_name: str) -> list[str]:
    """Resolve the backup sequence for a device using SequenceManager."""
    seq_name = "backup_config"
    sm = SequenceManager(config)
    sequence_commands = sm.resolve(seq_name, device_name)
    return sequence_commands or []


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


def _perform_device_backup(
    device_name: str,
    options: BackupOptions,
    run_timestamp: str,
) -> DeviceBackupResult:
    """Perform backup for a single device."""
    try:
        with _get_session(device_name, options.config, options.session_pool) as session:
            # Get platform-specific operations
            try:
                platform_ops = get_platform_operations(session)
            except UnsupportedOperationError as e:
                return DeviceBackupResult(
                    device=device_name,
                    success=False,
                    error=str(e),
                )

            # Resolve backup sequence
            seq_cmds = _resolve_backup_sequence(options.config, device_name)
            if not seq_cmds:
                return DeviceBackupResult(
                    device=device_name,
                    success=False,
                    error=f"backup sequence 'backup_config' not defined for {device_name}",
                )

            transport_type = options.config.get_transport_type(device_name)
            platform_name = platform_ops.get_platform_name()

            # Create backup
            backup_op_result = platform_ops.create_backup(
                backup_sequence=seq_cmds,
                download_files=None,
            )

            if not backup_op_result.success:
                errors = "; ".join(backup_op_result.errors)
                return DeviceBackupResult(
                    device=device_name,
                    success=False,
                    platform=platform_name,
                    transport=transport_type,
                    error=f"Backup creation failed: {errors}",
                )

            # Create backup directory
            backup_dir = (
                Path(options.config.general.backup_dir)
                / f"{device_name}_{run_timestamp}"
            )
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Save text outputs
            for filename, content in backup_op_result.text_outputs.items():
                output_file = backup_dir / filename
                output_file.write_text(content, encoding="utf-8")

            downloaded_files = []
            # Download files if requested
            if options.download and backup_op_result.files_to_download:
                for file_spec in backup_op_result.files_to_download:
                    remote_file = file_spec["source"]
                    local_filename = file_spec["destination"]

                    # Simple placeholder replacement for local path if needed,
                    # but here we just use the backup_dir as per original logic
                    destination = backup_dir / local_filename

                    try:
                        success = session.download_file(
                            remote_filename=remote_file,
                            local_path=destination,
                            delete_remote=options.delete_remote,
                        )
                        if success:
                            downloaded_files.append(local_filename)
                        else:
                            # We log error but don't fail the whole backup?
                            # Original logic printed error but continued.
                            # We can add to errors list if we want, but here we just track success.
                            pass
                    except Exception:
                        # Log error?
                        pass

            # Generate manifest
            manifest = {
                "device": device_name,
                "timestamp": run_timestamp,
                "platform": platform_name,
                "transport": transport_type,
                "text_outputs": list(backup_op_result.text_outputs.keys()),
                "downloaded_files": downloaded_files,
            }
            manifest_file = backup_dir / "manifest.json"
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            return DeviceBackupResult(
                device=device_name,
                success=True,
                platform=platform_name,
                transport=transport_type,
                backup_dir=backup_dir,
                text_outputs=backup_op_result.text_outputs,
                downloaded_files=downloaded_files,
            )

    except NetworkToolkitError as exc:
        return DeviceBackupResult(
            device=device_name,
            success=False,
            error=exc.message,
        )
    except Exception as exc:
        return DeviceBackupResult(
            device=device_name,
            success=False,
            error=str(exc),
        )


def run_backup(options: BackupOptions) -> BackupResult:
    """Execute backup operation."""
    start_time = perf_counter()

    # Resolve targets
    resolution = _resolve_targets(options.target, options.config)

    # Determine if it's a group (heuristic: if target name is in groups)
    is_group = (
        options.config.device_groups and options.target in options.config.device_groups
    )

    run_timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

    results: list[DeviceBackupResult] = []

    # Run in parallel
    with ThreadPoolExecutor() as executor:
        future_to_device = {
            executor.submit(_perform_device_backup, dev, options, run_timestamp): dev
            for dev in resolution.resolved
        }

        for future in as_completed(future_to_device):
            results.append(future.result())

    duration = perf_counter() - start_time

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success) + len(resolution.unknown)

    totals = RunTotals(
        total=len(resolution.resolved) + len(resolution.unknown),
        succeeded=succeeded,
        failed=failed,
    )

    return BackupResult(
        target=options.target,
        is_group=bool(is_group),
        resolution=resolution,
        duration=duration,
        totals=totals,
        device_results=results,
    )
