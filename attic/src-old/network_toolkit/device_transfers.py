"""Helpers for file transfer verification and utilities for device sessions.

This module provides small, focused functions that `DeviceSession` delegates to.
They are designed to avoid circular imports and rely only on a minimal session
interface: `execute_command(str) -> str` and a `.device_name` attribute for
logging context.
"""

from __future__ import annotations

import hashlib
import logging
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a local file efficiently."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def verify_file_upload(
    *,
    session: object,
    remote_filename: str,
    expected_size: int | None = None,
    expected_checksum: str | None = None,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> bool:
    """Verify remote file exists and matches expected size/checksum by downloading.

    This function provides robust verification by:
    1. Downloading the remote file to a temporary location
    2. Comparing file sizes (if expected_size provided)
    3. Comparing SHA256 checksums (if expected_checksum provided)
    4. Cleaning up the temporary downloaded file

    The `session` should provide:
    - `download_file(remote_filename: str, local_path: Path) -> bool`
    - `device_name: str`
    """
    device_name = getattr(session, "device_name", "<unknown>")

    for attempt in range(max_retries):
        temp_file: Path | None = None
        try:
            if attempt > 0:
                logger.info(
                    "Verification attempt %s/%s for '%s' on %s (wait %.1fs)",
                    attempt + 1,
                    max_retries,
                    remote_filename,
                    device_name,
                    retry_delay,
                )
                time.sleep(retry_delay)
            elif expected_size and expected_size > 1024 * 1024:
                # Slight extra wait for large files
                time.sleep(2.0)

            # Create temporary file for download verification
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f"_verify_{remote_filename}"
            ) as tmp:
                temp_file = Path(tmp.name)

            logger.debug(
                f"Downloading '{remote_filename}' to temporary file for "
                f"verification: {temp_file}"
            )

            # Download the file to verify it exists and is accessible
            try:
                download_success = session.download_file(  # type: ignore[attr-defined]
                    remote_filename=remote_filename,
                    local_path=temp_file,
                    delete_remote=False,  # Don't delete the remote file
                    verify_download=False,  # Don't create recursive verification
                )

                if not download_success:
                    logger.warning(
                        f"Download failed for verification on attempt {attempt + 1}"
                    )
                    if attempt == max_retries - 1:
                        logger.error(
                            f"File '{remote_filename}' could not be downloaded "
                            f"for verification on {device_name}"
                        )
                        return False
                    continue

            except Exception as e:
                logger.warning(
                    f"Download failed during verification attempt {attempt + 1}: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(
                        f"File '{remote_filename}' verification failed on "
                        f"{device_name}: {e}"
                    )
                    return False
                continue

            # Verify the downloaded file exists
            if not temp_file.exists():
                logger.warning(f"Downloaded file does not exist: {temp_file}")
                if attempt == max_retries - 1:
                    return False
                continue

            # Check file size if expected
            if expected_size is not None:
                downloaded_size = temp_file.stat().st_size
                if downloaded_size != expected_size:
                    logger.error(
                        f"File size mismatch for '{remote_filename}' on "
                        f"{device_name}: expected {expected_size} bytes, "
                        f"got {downloaded_size} bytes"
                    )
                    if attempt == max_retries - 1:
                        return False
                    continue
                logger.debug(f"File size verification passed: {downloaded_size} bytes")

            # Check checksum if expected
            if expected_checksum is not None:
                downloaded_checksum = calculate_file_checksum(temp_file)
                if downloaded_checksum != expected_checksum:
                    logger.error(
                        f"Checksum mismatch for '{remote_filename}' on "
                        f"{device_name}: expected {expected_checksum}, "
                        f"got {downloaded_checksum}"
                    )
                    if attempt == max_retries - 1:
                        return False
                    continue
                logger.debug(f"Checksum verification passed: {downloaded_checksum}")

            logger.info(
                f"File upload verification successful for '{remote_filename}' "
                f"on {device_name}"
            )
            return True

        except Exception as e:
            logger.warning(f"Could not verify file upload on {device_name}: {e}")
            if attempt == max_retries - 1:
                return False

        finally:
            # Clean up temporary file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary verification file: {temp_file}")
                except Exception as e:
                    logger.warning(
                        f"Failed to clean up temporary file {temp_file}: {e}"
                    )

    return False
