"""Programmatic API for executing commands and sequences without the CLI."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

from network_toolkit.common.credentials import InteractiveCredentials
from network_toolkit.config import NetworkConfig
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.ip_device import (
    create_ip_based_config as _create_ip_based_config,
)
from network_toolkit.ip_device import (
    extract_ips_from_target,
    get_supported_platforms,
    is_ip_list,
    validate_platform,
)
from network_toolkit.results_enhanced import ResultsManager
from network_toolkit.sequence_manager import SequenceManager
from network_toolkit.transport.factory import get_transport_factory


@dataclass(slots=True)
class TargetResolution:
    """Resolved target information."""

    resolved: list[str]
    unknown: list[str]
    ip_mode: bool = False


@dataclass(slots=True)
class RunTotals:
    """Aggregate run statistics."""

    total: int
    succeeded: int
    failed: int


@dataclass(slots=True)
class DeviceCommandResult:
    """Result of executing a single command on a device."""

    device: str
    command: str
    output: str | None
    error: str | None = None
    stored_path: Path | None = None


@dataclass(slots=True)
class DeviceSequenceResult:
    """Result of executing a sequence on a device."""

    device: str
    sequence: str
    outputs: dict[str, str] | None
    error: str | None = None
    stored_paths: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class RunOptions:
    """Typed inputs for running commands programmatically."""

    target: str
    command_or_sequence: str
    config: NetworkConfig
    device_type: str | None = None
    port: int | None = None
    transport_type: str | None = None
    interactive_creds: InteractiveCredentials | None = None
    store_results: bool = False
    results_dir: str | None = None
    no_strict_host_key_checking: bool = False


@dataclass(slots=True)
class RunResult:
    """Typed output representing an execution run."""

    target: str
    command_or_sequence: str
    is_sequence: bool
    is_group: bool
    resolution: TargetResolution
    duration: float
    totals: RunTotals
    command_results: list[DeviceCommandResult] = field(default_factory=list)
    sequence_results: list[DeviceSequenceResult] = field(default_factory=list)
    results_dir: Path | None = None
    notices: list[str] = field(default_factory=list)


class TargetResolutionError(NetworkToolkitError):
    """Raised when targets cannot be resolved."""

    def __init__(self, message: str, unknown_targets: list[str] | None = None) -> None:
        super().__init__(message, details={"unknown_targets": unknown_targets or []})
        self.unknown_targets = unknown_targets or []


def _validate_transport(transport_type: str | None) -> None:
    """Ensure the requested transport exists."""
    if transport_type is None:
        return
    get_transport_factory(transport_type)


def _apply_host_key_setting(
    config: NetworkConfig, *, no_strict_host_key_checking: bool
) -> None:
    if no_strict_host_key_checking:
        if hasattr(config, "general") and hasattr(
            config.general, "ssh_strict_host_key_checking"
        ):
            config.general.ssh_strict_host_key_checking = False


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


def _build_results_manager(
    config: NetworkConfig,
    *,
    store_results: bool,
    results_dir: str | None,
    command_context: str,
) -> ResultsManager:
    return ResultsManager(
        config,
        store_results=store_results,
        results_dir=results_dir,
        command_context=command_context,
    )


def _run_command_on_device(
    device_name: str,
    config: NetworkConfig,
    command: str,
    username_override: str | None,
    password_override: str | None,
    transport_override: str | None,
    results_mgr: ResultsManager,
) -> DeviceCommandResult:
    from network_toolkit.device import DeviceSession

    try:
        with DeviceSession(
            device_name,
            config,
            username_override,
            password_override,
            transport_override,
        ) as session:
            output = session.execute_command(command)
    except NetworkToolkitError as exc:
        return DeviceCommandResult(
            device=device_name,
            command=command,
            output=None,
            error=exc.message,
        )
    except Exception as exc:  # pragma: no cover - unexpected path
        return DeviceCommandResult(
            device=device_name,
            command=command,
            output=None,
            error=str(exc),
        )

    stored_path = results_mgr.store_command_result(device_name, command, output)
    return DeviceCommandResult(
        device=device_name,
        command=command,
        output=output,
        error=None,
        stored_path=stored_path,
    )


def _run_sequence_on_device(
    device_name: str,
    config: NetworkConfig,
    sequence_name: str,
    username_override: str | None,
    password_override: str | None,
    transport_override: str | None,
    results_mgr: ResultsManager,
    sequence_manager: SequenceManager,
) -> DeviceSequenceResult:
    from network_toolkit.device import DeviceSession

    try:
        commands = sequence_manager.resolve(sequence_name, device_name)
        if not commands:
            msg = f"Sequence '{sequence_name}' not found for device type"
            return DeviceSequenceResult(
                device=device_name,
                sequence=sequence_name,
                outputs=None,
                error=msg,
            )

        outputs: dict[str, str] = {}
        with DeviceSession(
            device_name,
            config,
            username_override,
            password_override,
            transport_override,
        ) as session:
            for cmd in commands:
                outputs[cmd] = session.execute_command(cmd)
    except NetworkToolkitError as exc:
        return DeviceSequenceResult(
            device=device_name,
            sequence=sequence_name,
            outputs=None,
            error=exc.message,
        )
    except Exception as exc:  # pragma: no cover - unexpected path
        return DeviceSequenceResult(
            device=device_name,
            sequence=sequence_name,
            outputs=None,
            error=str(exc),
        )

    stored_paths = results_mgr.store_sequence_results(
        device_name, sequence_name, outputs
    )
    return DeviceSequenceResult(
        device=device_name,
        sequence=sequence_name,
        outputs=outputs,
        error=None,
        stored_paths=stored_paths,
    )


def _prepare_config_for_ips(
    target: str,
    config: NetworkConfig,
    device_type: str | None,
    port: int | None,
    transport_type: str | None,
) -> tuple[NetworkConfig, list[str]]:
    ips = extract_ips_from_target(target)
    if device_type is None:
        supported = get_supported_platforms()
        msg = "When using IP addresses, --platform is required"
        raise TargetResolutionError(msg, unknown_targets=list(supported.keys()))

    if not validate_platform(device_type):
        supported = get_supported_platforms()
        msg = f"Invalid device type '{device_type}'"
        raise TargetResolutionError(msg, unknown_targets=list(supported.keys()))

    enriched_config = _create_ip_based_config(
        ips, device_type, config, port=port, transport_type=transport_type
    )
    return enriched_config, ips


def run_commands(options: RunOptions) -> RunResult:
    """
    Execute a command or sequence across one or more devices without CLI side effects.

    Raises
    ------
    TargetResolutionError
        If no devices can be resolved for the given target(s)
    NetworkToolkitError
        For configuration or execution errors that prevent the run
    """

    _validate_transport(options.transport_type)

    config = options.config
    notices: list[str] = []

    _apply_host_key_setting(
        config, no_strict_host_key_checking=options.no_strict_host_key_checking
    )

    # IP-based targets may require dynamic config creation
    if is_ip_list(options.target):
        config, ips = _prepare_config_for_ips(
            options.target,
            config,
            options.device_type,
            options.port,
            options.transport_type,
        )
        notices.append(
            f"Using IP addresses with device type '{options.device_type}': {', '.join(ips)}"
        )

    sequence_manager = SequenceManager(config)
    command_context = f"run_{options.target}_{options.command_or_sequence}"
    results_mgr = _build_results_manager(
        config=config,
        store_results=options.store_results,
        results_dir=options.results_dir,
        command_context=command_context,
    )

    resolution = _resolve_targets(options.target, config)
    if not resolution.resolved:
        msg = f"No devices resolved for target '{options.target}'"
        raise TargetResolutionError(msg, unknown_targets=resolution.unknown)

    is_sequence = bool(sequence_manager.exists(options.command_or_sequence))
    is_group = len(resolution.resolved) > 1

    # Get credential overrides if requested
    username_override = (
        options.interactive_creds.username if options.interactive_creds else None
    )
    password_override = (
        options.interactive_creds.password if options.interactive_creds else None
    )

    started_at = perf_counter()

    if is_sequence:
        if is_group:
            with ThreadPoolExecutor(max_workers=len(resolution.resolved)) as executor:
                future_to_device = {
                    executor.submit(
                        _run_sequence_on_device,
                        device,
                        config,
                        options.command_or_sequence,
                        username_override,
                        password_override,
                        options.transport_type,
                        results_mgr,
                        sequence_manager,
                    ): device
                    for device in resolution.resolved
                }
                sequence_results = [
                    future.result() for future in as_completed(future_to_device)
                ]
        else:
            sequence_results = [
                _run_sequence_on_device(
                    resolution.resolved[0],
                    config,
                    options.command_or_sequence,
                    username_override,
                    password_override,
                    options.transport_type,
                    results_mgr,
                    sequence_manager,
                )
            ]

        totals = RunTotals(
            total=len(sequence_results),
            succeeded=sum(1 for r in sequence_results if not r.error),
            failed=sum(1 for r in sequence_results if r.error),
        )

        # Group summary stored after all device results are available
        if is_group:
            order_index = {name: idx for idx, name in enumerate(resolution.resolved)}
            sequence_results.sort(key=lambda r: order_index.get(r.device, 0))

        if is_group and options.store_results:
            results_mgr.store_group_results(
                group_name=options.target,
                command_or_sequence=options.command_or_sequence,
                group_results=[
                    (r.device, r.outputs, r.error) for r in sequence_results
                ],
                is_sequence=True,
            )

        duration = perf_counter() - started_at
        return RunResult(
            target=options.target,
            command_or_sequence=options.command_or_sequence,
            is_sequence=True,
            is_group=is_group,
            resolution=resolution,
            duration=duration,
            totals=totals,
            sequence_results=sequence_results,
            results_dir=results_mgr.session_dir,
            notices=notices,
        )

    # Command mode
    if is_group:
        with ThreadPoolExecutor(max_workers=len(resolution.resolved)) as executor:
            future_to_device_cmd = {
                executor.submit(
                    _run_command_on_device,
                    device,
                    config,
                    options.command_or_sequence,
                    username_override,
                    password_override,
                    options.transport_type,
                    results_mgr,
                ): device
                for device in resolution.resolved
            }
            command_results = [
                future.result() for future in as_completed(future_to_device_cmd)
            ]
        order_index = {name: idx for idx, name in enumerate(resolution.resolved)}
        command_results.sort(key=lambda r: order_index.get(r.device, 0))
    else:
        command_results = [
            _run_command_on_device(
                resolution.resolved[0],
                config,
                options.command_or_sequence,
                username_override,
                password_override,
                options.transport_type,
                results_mgr,
            )
        ]

    totals = RunTotals(
        total=len(command_results),
        succeeded=sum(1 for r in command_results if not r.error),
        failed=sum(1 for r in command_results if r.error),
    )

    if is_group and options.store_results:
        results_mgr.store_group_results(
            group_name=options.target,
            command_or_sequence=options.command_or_sequence,
            group_results=[(r.device, r.output, r.error) for r in command_results],
            is_sequence=False,
        )

    duration = perf_counter() - started_at
    return RunResult(
        target=options.target,
        command_or_sequence=options.command_or_sequence,
        is_sequence=False,
        is_group=is_group,
        resolution=resolution,
        duration=duration,
        totals=totals,
        command_results=command_results,
        results_dir=results_mgr.session_dir,
        notices=notices,
    )
