# File Upload Functionality for MikroTik Devices

This document describes the file upload functionality added to the `DeviceSession` class, which allows uploading files to MikroTik RouterOS devices using SCP (Secure Copy Protocol).

## Features

- **Single Device Upload**: Upload files to individual MikroTik devices
- **Batch Upload**: Upload files to multiple devices concurrently
- **File Verification**: Automatically verify successful uploads
- **Error Handling**: Comprehensive error handling and logging
- **File Safety**: Prevents file truncation with proper error checking
- **Concurrent Processing**: Support for uploading to multiple devices simultaneously

## Usage

### Single Device Upload

```python
from network_toolkit.config import load_config
from network_toolkit.device import DeviceSession
from pathlib import Path

# Load configuration from default location
config = load_config()

# Upload a file to a single device
with DeviceSession("router1", config) as session:
    success = session.upload_file(
        local_path="config_backup.rsc",
        remote_filename="uploaded_config.rsc",  # Optional: custom remote name
        verify_upload=True  # Optional: verify the upload
    )

    if success:
        print("File uploaded successfully!")
    else:
        print("File upload failed!")
```

### Multiple Device Upload

```python
from network_toolkit.device import DeviceSession

# Upload to multiple devices concurrently
results = DeviceSession.upload_file_to_devices(
    device_names=["router1", "router2", "switch1"],
    config=config,
    local_path="firmware.npk",
    remote_filename="new_firmware.npk",
    verify_upload=True,
    max_concurrent=3  # Upload to max 3 devices at once
)

# Check results
for device, success in results.items():
    status = "SUCCESS" if success else "FAILED"
    print(f"{device}: {status}")
```

## Method Reference

### `DeviceSession.upload_file()`

Upload a file to a single MikroTik device.

**Parameters:**
- `local_path` (str | Path): Path to the local file to upload
- `remote_filename` (str | None, optional): Name for the file on the remote device. If None, uses the original filename
- `verify_upload` (bool, default=True): Whether to verify the upload by checking if the file exists on the device

**Returns:**
- `bool`: True if upload was successful, False otherwise

**Raises:**
- `DeviceExecutionError`: If device is not connected or upload fails
- `FileNotFoundError`: If local file does not exist
- `ValueError`: If local path is not a file

### `DeviceSession.upload_file_to_devices()` (Static Method)

Upload a file to multiple devices concurrently.

**Parameters:**
- `device_names` (list[str]): List of device names to upload to
- `config` (NetworkConfig): Network configuration containing device settings
- `local_path` (str | Path): Path to the local file to upload
- `remote_filename` (str | None, optional): Name for the file on remote devices
- `verify_upload` (bool, default=True): Whether to verify uploads
- `max_concurrent` (int, default=5): Maximum number of concurrent uploads

**Returns:**
- `dict[str, bool]`: Dictionary mapping device names to upload success status

**Raises:**
- `FileNotFoundError`: If local file does not exist
- `ValueError`: If local path is not a file

## File Safety Features

### Preventing File Truncation

The implementation includes several safety measures to prevent file truncation:

1. **File Existence Check**: Verifies local file exists before attempting upload
2. **File Type Verification**: Ensures the path points to a file (not directory)
3. **Size Logging**: Logs file size before upload for verification
4. **Upload Verification**: Optionally verifies file appears on remote device
5. **Error Handling**: Proper exception handling with detailed error messages

### Connection Management

- **Transport Cleanup**: Properly closes SFTP and transport connections
- **Exception Safety**: Uses try/finally blocks to ensure cleanup
- **Authentication Handling**: Specific handling for authentication failures

## Error Handling

The upload functionality provides comprehensive error handling:

- **Authentication Errors**: Specific handling for SSH authentication failures
- **SSH Errors**: General SSH connection and transfer errors
- **File System Errors**: Local file not found or permission issues
- **Network Errors**: Connection timeouts and network failures
- **Verification Errors**: Upload verification failures

All errors are logged with appropriate detail levels and include context information.

## Usage Examples

Here are common file upload scenarios:

1. Single file upload with verification
2. Batch upload to multiple devices
3. RouterOS script file upload and execution
4. Error handling patterns

## Best Practices

1. **Always verify uploads** for critical files
2. **Use appropriate concurrency limits** to avoid overwhelming devices
3. **Check file sizes** before uploading large files
4. **Handle errors gracefully** in production code
5. **Use meaningful remote filenames** for organization
6. **Monitor upload progress** for large batch operations

## Supported File Types

The upload functionality supports any file type that MikroTik RouterOS can handle:

- Configuration files (`.rsc`)
- Firmware files (`.npk`)
- Certificate files (`.crt`, `.key`)
- Script files (`.rsc`)
- Backup files (`.backup`)
- Binary files and others

## Dependencies

The file upload functionality requires:

- `paramiko`: For SCP/SFTP functionality
- `scrapli`: For SSH connections and verification
- `concurrent.futures`: For concurrent uploads (Python standard library)
- `threading`: For thread-safe logging (Python standard library)

## Logging

The implementation provides detailed logging at different levels:

- **INFO**: Upload start/completion, verification results, batch summaries
- **DEBUG**: File sizes, detailed progress information
- **WARNING**: Non-critical issues like verification failures
- **ERROR**: Upload failures, authentication errors, critical issues

Configure logging level as needed for your use case.
