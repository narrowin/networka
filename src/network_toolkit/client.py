"""High-level Python client for Networka."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from network_toolkit.common.credentials import InteractiveCredentials
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.sequence_manager import SequenceManager

if TYPE_CHECKING:
    from types import TracebackType

    from network_toolkit.api.backup import BackupResult
    from network_toolkit.api.diff import DiffResult
    from network_toolkit.api.download import DownloadResult
    from network_toolkit.api.run import RunResult
    from network_toolkit.api.upload import UploadResult
    from network_toolkit.config import DeviceConfig, DeviceGroup
    from network_toolkit.device import DeviceSession


class NetworkaClient:
    """
    A high-level client for interacting with the Networka library.

    This client encapsulates configuration loading and provides a unified interface
    for executing commands, running backups, transferring files, and more.

    Usage:
        >>> from network_toolkit import NetworkaClient
        >>> # Use as context manager for automatic session reuse
        >>> with NetworkaClient() as client:
        >>>     client.run("router1", "show version")
        >>>     client.run("router1", "show ip int brief")
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        """
        Initialize the Networka client.

        Args:
            config_path: Path to the configuration directory or file.
                         If None, defaults to standard locations.
        """
        self._config_path = config_path or DEFAULT_CONFIG_PATH
        self._config: NetworkConfig | None = None
        self._sequence_manager: SequenceManager | None = None
        self._sessions: dict[str, DeviceSession] = {}

    @property
    def config(self) -> NetworkConfig:
        """Lazy-load and return the network configuration."""
        if self._config is None:
            self._config = load_config(self._config_path)
        return self._config

    @property
    def sequence_manager(self) -> SequenceManager:
        """Lazy-load and return the sequence manager."""
        if self._sequence_manager is None:
            self._sequence_manager = SequenceManager(self.config)
        return self._sequence_manager

    @property
    def devices(self) -> dict[str, DeviceConfig]:
        """Return the dictionary of configured devices."""
        return self.config.devices or {}

    @property
    def groups(self) -> dict[str, DeviceGroup]:
        """Return the dictionary of configured device groups."""
        return self.config.device_groups or {}

    def run(
        self,
        target: str,
        command_or_sequence: str,
        *,
        device_type: str | None = None,
        port: int | None = None,
        transport_type: str | None = None,
        interactive_creds: InteractiveCredentials | None = None,
        store_results: bool = False,
        results_dir: str | None = None,
        no_strict_host_key_checking: bool = False,
    ) -> RunResult:
        """
        Execute a command or sequence on one or more targets.

        Args:
            target: Device name, group name, or IP address.
            command_or_sequence: Command string or sequence name to execute.
            device_type: Platform type (required for IP targets).
            port: SSH port (optional).
            transport_type: Transport protocol (e.g., "ssh", "telnet").
            interactive_creds: Credentials to use if not in config.
            store_results: Whether to save output to files.
            results_dir: Directory to save results (if store_results is True).
            no_strict_host_key_checking: Disable strict host key checking.

        Returns:
            RunResult object containing execution details and outputs.
        """
        from network_toolkit.api.run import RunOptions, run_commands

        options = RunOptions(
            target=target,
            command_or_sequence=command_or_sequence,
            config=self.config,
            device_type=device_type,
            port=port,
            transport_type=transport_type,
            interactive_creds=interactive_creds,
            store_results=store_results,
            results_dir=results_dir,
            no_strict_host_key_checking=no_strict_host_key_checking,
            session_pool=self._sessions,
        )
        return run_commands(options)

    def backup(
        self,
        target: str,
        *,
        download: bool = True,
        delete_remote: bool = False,
        verbose: bool = False,
    ) -> BackupResult:
        """
        Perform a configuration backup on one or more targets.

        Args:
            target: Device name, group name, or IP address.
            download: Whether to download the backup file to local disk.
            delete_remote: Whether to delete the backup file from the device after download.
            verbose: Enable verbose logging.

        Returns:
            BackupResult object containing backup status and file paths.
        """
        from network_toolkit.api.backup import BackupOptions, run_backup

        options = BackupOptions(
            target=target,
            config=self.config,
            download=download,
            delete_remote=delete_remote,
            verbose=verbose,
        )
        return run_backup(options)

    def diff(
        self,
        targets: str,
        subject: str,
        *,
        baseline: Path | None = None,
        ignore_patterns: list[str] | None = None,
        save_current: Path | None = None,
        store_results: bool = False,
        results_dir: str | None = None,
        verbose: bool = False,
    ) -> DiffResult:
        """
        Compare current device state against a baseline.

        Args:
            targets: Device name, group name, or IP address.
            subject: Command or sequence to run and compare.
            baseline: Path to baseline file or directory.
            ignore_patterns: Regex patterns to ignore in diff.
            save_current: Path to save the current output.
            store_results: Whether to save diff results.
            results_dir: Directory to save results.
            verbose: Enable verbose logging.

        Returns:
            DiffResult object containing diff outcomes.
        """
        from network_toolkit.api.diff import DiffOptions, diff_targets

        options = DiffOptions(
            targets=targets,
            subject=subject,
            config=self.config,
            baseline=baseline,
            ignore_patterns=ignore_patterns,
            save_current=save_current,
            store_results=store_results,
            results_dir=results_dir,
            verbose=verbose,
        )
        return diff_targets(options)

    def download(
        self,
        target: str,
        remote_file: str,
        local_path: Path | str,
        *,
        delete_remote: bool = False,
        verify_download: bool = True,
        verbose: bool = False,
    ) -> DownloadResult:
        """
        Download a file from one or more targets.

        Args:
            target: Device name, group name, or IP address.
            remote_file: Path to the file on the remote device.
            local_path: Local path to save the downloaded file.
            delete_remote: Whether to delete the remote file after download.
            verify_download: Whether to verify the download.
            verbose: Enable verbose logging.

        Returns:
            DownloadResult object.
        """
        from network_toolkit.api.download import DownloadOptions, download_file

        options = DownloadOptions(
            target=target,
            remote_file=remote_file,
            local_path=Path(local_path),
            config=self.config,
            delete_remote=delete_remote,
            verify_download=verify_download,
            verbose=verbose,
        )
        return download_file(options)

    def upload(
        self,
        target: str,
        local_file: Path | str,
        *,
        remote_filename: str | None = None,
        verify: bool = True,
        checksum_verify: bool = False,
        max_concurrent: int = 5,
        verbose: bool = False,
    ) -> UploadResult:
        """
        Upload a file to one or more targets.

        Args:
            target: Device name, group name, or IP address.
            local_file: Path to the local file to upload.
            remote_filename: Destination filename on the remote device.
            verify: Whether to verify the upload.
            checksum_verify: Whether to verify using checksums.
            max_concurrent: Maximum concurrent uploads.
            verbose: Enable verbose logging.

        Returns:
            UploadResult object.
        """
        from network_toolkit.api.upload import UploadOptions, upload_file

        options = UploadOptions(
            target=target,
            local_file=Path(local_file),
            config=self.config,
            remote_filename=remote_filename,
            verify=verify,
            checksum_verify=checksum_verify,
            max_concurrent=max_concurrent,
            verbose=verbose,
        )
        return upload_file(options)

    def close(self) -> None:
        """Close all active device sessions."""
        for session in self._sessions.values():
            try:
                session.disconnect()
            except Exception:
                pass
        self._sessions.clear()

    def __enter__(self) -> NetworkaClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
