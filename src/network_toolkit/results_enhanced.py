"""Enhanced results storage utilities for network toolkit."""

from __future__ import annotations

import datetime as dt
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import yaml

from network_toolkit.common.filename_utils import normalize_filename

if TYPE_CHECKING:
    from network_toolkit.config import NetworkConfig

logger = logging.getLogger(__name__)

# Constants
MAX_FILENAME_LEN = 100


class ResultsManager:
    """
    Enhanced results manager that creates individual files per device and command.

    Features:
    - Creates one session directory per run and reuses it for all outputs
    - Individual files per device and command
    - Proper file naming with underscores
    - Support for multiple output formats
    """

    def __init__(
        self,
        config: NetworkConfig,
        *,
        store_results: bool | None = None,
        results_dir: str | Path | None = None,
        command_context: str | None = None,
    ) -> None:
        """Initialize results manager."""
        self.config = config
        self.store_results = (
            store_results if store_results is not None else config.general.store_results
        )
        self.results_dir = (
            Path(results_dir) if results_dir else Path(config.general.results_dir)
        )
        self.results_format = config.general.results_format
        self.include_timestamp = config.general.results_include_timestamp
        self.include_command = config.general.results_include_command
        self.command_context = command_context  # Store the nw command used
        # Cached session directory for this run
        self.session_dir: Path | None = None

        # Create results directory if it doesn't exist and initialize session folder
        if self.store_results:
            self.results_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Results will be stored in: {self.results_dir}")
            # Create a single session directory at the start of the run
            self.session_dir = self._create_session_directory()

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filenames.

        Uses centralized filename normalization from filename_utils module.
        """
        return normalize_filename(text, max_length=MAX_FILENAME_LEN)

    def _create_session_directory(self) -> Path:
        """Create a directory for this execution session."""
        timestamp = datetime.now(tz=dt.UTC).strftime("%Y%m%d_%H%M%S")

        # Create session folder name with command context
        session_name_parts = [timestamp]
        if self.command_context:
            # Sanitize command context for folder name
            sanitized_cmd = self._sanitize_filename(self.command_context)
            session_name_parts.append(sanitized_cmd)

        session_dir_name = "_".join(session_name_parts)
        session_dir = self.results_dir / session_dir_name
        session_dir.mkdir(parents=True, exist_ok=True)

        return session_dir

    def store_command_result(
        self,
        device_name: str,
        command: str,
        output: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path | None:
        """Store a single command result to file in device-specific directory."""
        if not self.store_results:
            return None

        session_dir = self.session_dir or self._create_session_directory()
        device_dir = session_dir / self._sanitize_filename(device_name)
        device_dir.mkdir(parents=True, exist_ok=True)

        cmd_filename = f"cmd_{self._sanitize_filename(command)}.{self.results_format}"
        filepath = device_dir / cmd_filename

        result_data: dict[str, Any] = {
            "timestamp": datetime.now(tz=dt.UTC).isoformat(),
            "device_name": device_name,
            "command": command,
            "output": output,
            "nw_command": self.command_context,
            "metadata": metadata or {},
        }

        try:
            self._write_result_file(filepath, result_data, is_single_command=True)
            logger.debug(f"Stored command result: {filepath}")
            return filepath
        except Exception as e:  # pragma: no cover - filesystem error
            logger.error(f"Failed to store command result to {filepath}: {e}")
            return None

    def store_sequence_results(
        self,
        device_name: str,
        sequence_name: str,
        results: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Store command sequence results to individual files per command."""
        if not self.store_results:
            return []

        session_dir = self.session_dir or self._create_session_directory()
        device_dir = session_dir / self._sanitize_filename(device_name)
        device_dir.mkdir(parents=True, exist_ok=True)

        stored_files: list[Path] = []
        for i, (command, output) in enumerate(results.items(), 1):
            cmd_filename = (
                f"{i:02d}_{self._sanitize_filename(command)}.{self.results_format}"
            )
            filepath = device_dir / cmd_filename

            result_data: dict[str, Any] = {
                "timestamp": datetime.now(tz=dt.UTC).isoformat(),
                "device_name": device_name,
                "sequence_name": sequence_name,
                "command_number": i,
                "total_commands": len(results),
                "command": command,
                "output": output,
                "nw_command": self.command_context,
                "metadata": metadata or {},
            }

            try:
                self._write_result_file(filepath, result_data, is_single_command=True)
                stored_files.append(filepath)
                logger.debug(f"Stored command result: {filepath}")
            except Exception as e:  # pragma: no cover - filesystem error
                logger.error(f"Failed to store command result to {filepath}: {e}")

        summary_filename = (
            f"00_sequence_summary_{self._sanitize_filename(sequence_name)}."
            f"{self.results_format}"
        )
        summary_filepath = device_dir / summary_filename
        summary_data: dict[str, Any] = {
            "timestamp": datetime.now(tz=dt.UTC).isoformat(),
            "device_name": device_name,
            "sequence_name": sequence_name,
            "commands_executed": len(results),
            "nw_command": self.command_context,
            "results_summary": {
                cmd: f"Command {i + 1}: {cmd}" for i, cmd in enumerate(results.keys())
            },
            "metadata": metadata or {},
        }

        try:
            self._write_result_file(
                summary_filepath, summary_data, is_single_command=False
            )
            stored_files.append(summary_filepath)
            logger.debug(f"Stored sequence summary: {summary_filepath}")
        except Exception as e:  # pragma: no cover - filesystem error
            logger.error(f"Failed to store sequence summary to {summary_filepath}: {e}")

        return stored_files

    def store_group_results(
        self,
        group_name: str,
        command_or_sequence: str,
        group_results: list[tuple[str, Any, str | None]],
        *,
        is_sequence: bool = False,
    ) -> list[Path]:
        """Store group command/sequence results to individual files per device."""
        if not self.store_results:
            return []

        session_dir = self.session_dir or self._create_session_directory()
        stored_files: list[Path] = []

        for device_name, device_results, error in group_results:
            device_dir = session_dir / self._sanitize_filename(device_name)
            device_dir.mkdir(parents=True, exist_ok=True)

            if error:
                error_filename = (
                    f"ERROR_{self._sanitize_filename(command_or_sequence)}."
                    f"{self.results_format}"
                )
                error_filepath = device_dir / error_filename

                error_data: dict[str, Any] = {
                    "timestamp": datetime.now(tz=dt.UTC).isoformat(),
                    "device_name": device_name,
                    "group_name": group_name,
                    "command_or_sequence": command_or_sequence,
                    "type": "sequence" if is_sequence else "command",
                    "status": "failed",
                    "error": error,
                    "nw_command": self.command_context,
                }

                try:
                    self._write_result_file(
                        error_filepath, error_data, is_single_command=True
                    )
                    stored_files.append(error_filepath)
                except Exception as e:  # pragma: no cover - filesystem error
                    logger.error(f"Failed to store error file to {error_filepath}: {e}")

            elif is_sequence and isinstance(device_results, dict):
                files = self.store_sequence_results(
                    device_name,
                    command_or_sequence,
                    cast(dict[str, str], device_results),
                )
                stored_files.extend(files)
            else:
                file_path = self.store_command_result(
                    device_name, command_or_sequence, str(device_results)
                )
                if file_path:
                    stored_files.append(file_path)

        group_summary_filename = (
            f"GROUP_SUMMARY_{self._sanitize_filename(group_name)}_"
            f"{self._sanitize_filename(command_or_sequence)}.{self.results_format}"
        )
        group_summary_filepath = session_dir / group_summary_filename

        succeeded_devices = [name for name, _, error in group_results if not error]
        failed_devices = [name for name, _, error in group_results if error]

        group_summary_data: dict[str, Any] = {
            "timestamp": datetime.now(tz=dt.UTC).isoformat(),
            "group_name": group_name,
            "command_or_sequence": command_or_sequence,
            "type": "sequence" if is_sequence else "command",
            "nw_command": self.command_context,
            "total_devices": len(group_results),
            "succeeded_devices": len(succeeded_devices),
            "failed_devices": len(failed_devices),
            "succeeded_device_list": succeeded_devices,
            "failed_device_list": failed_devices,
        }

        try:
            self._write_result_file(
                group_summary_filepath, group_summary_data, is_single_command=False
            )
            stored_files.append(group_summary_filepath)
            logger.debug(f"Stored group summary: {group_summary_filepath}")
        except Exception as e:  # pragma: no cover - filesystem error
            logger.error(
                f"Failed to store group summary to {group_summary_filepath}: {e}"
            )

        return stored_files

    def _write_result_file(
        self, filepath: Path, data: dict[str, Any], *, is_single_command: bool
    ) -> None:
        """Write result data to file in the configured format."""
        if self.results_format == "json":
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif self.results_format == "yaml":
            with filepath.open("w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        else:  # txt format (default)
            with filepath.open("w", encoding="utf-8") as f:
                f.write("# Network Toolkit Results\n")
                f.write(f"# Generated: {data['timestamp']}\n")
                f.write(f"# Device: {data['device_name']}\n")
                if data.get("nw_command"):
                    f.write(f"# NW Command: {data['nw_command']}\n")
                f.write("\n")

                if is_single_command:
                    if "sequence_name" in data:
                        f.write(f"Sequence: {data['sequence_name']}\n")
                        f.write(
                            "Command "
                            f"{data['command_number']}/{data['total_commands']}: "
                            f"{data['command']}\n"
                        )
                    else:
                        f.write(f"Command: {data['command']}\n")
                    f.write("=" * 80 + "\n\n")

                    if data.get("output"):
                        f.write(data["output"])
                    else:
                        f.write("(no output)")
                    f.write("\n")

                elif "group_name" in data:
                    # Summary file for group
                    f.write(f"Group: {data['group_name']}\n")
                    f.write(f"Total Devices: {data['total_devices']}\n")
                    f.write(f"Succeeded: {data['succeeded_devices']}\n")
                    f.write(f"Failed: {data['failed_devices']}\n")
                    f.write("=" * 80 + "\n\n")

                    if data.get("succeeded_device_list"):
                        f.write("Succeeded Devices:\n")
                        for device in data["succeeded_device_list"]:
                            f.write(f"  - {device}\n")
                        f.write("\n")

                    if data.get("failed_device_list"):
                        f.write("Failed Devices:\n")
                        for device in data["failed_device_list"]:
                            f.write(f"  - {device}\n")
                        f.write("\n")

                elif "sequence_name" in data:
                    # Summary file for sequence
                    f.write(f"Sequence: {data['sequence_name']}\n")
                    f.write(f"Commands executed: {data['commands_executed']}\n")
                    f.write("=" * 80 + "\n\n")

                    if data.get("results_summary"):
                        f.write("Commands in sequence:\n")
                        for _, desc in data["results_summary"].items():
                            f.write(f"  - {desc}\n")
                        f.write("\n")
