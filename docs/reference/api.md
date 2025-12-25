# API Reference

Complete reference documentation for Networka's Python API.

## Core Classes

### NetworkaClient

High-level client for all Networka operations.

::: network_toolkit.client.NetworkaClient
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - config
        - devices
        - groups
        - run
        - backup
        - diff
        - download
        - upload

### DeviceSession

Persistent session manager for network device connections.

::: network_toolkit.device.DeviceSession
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - connect
        - disconnect
        - execute_command
        - upload_file
        - download_file

## Utilities

### create_ip_based_config

Create device configurations from IP addresses.

::: network_toolkit.ip_device.create_ip_based_config
    options:
      show_root_heading: true
      show_source: false

## Exceptions

All Networka exceptions inherit from `NetworkToolkitError`.

::: network_toolkit.exceptions.NetworkToolkitError
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.exceptions.DeviceConnectionError
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.exceptions.DeviceExecutionError
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.exceptions.FileTransferError
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.exceptions.ConfigurationError
    options:
      show_root_heading: true
      show_source: false

## Result Types

Result objects returned by various operations.

### Run Results

::: network_toolkit.api.run.RunResult
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.run.DeviceCommandResult
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.run.DeviceSequenceResult
    options:
      show_root_heading: true
      show_source: false

### Backup Results

::: network_toolkit.api.backup.BackupResult
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.backup.DeviceBackupResult
    options:
      show_root_heading: true
      show_source: false

### Diff Results

::: network_toolkit.api.diff.DiffResult
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.diff.DiffItemResult
    options:
      show_root_heading: true
      show_source: false

### Transfer Results

::: network_toolkit.api.download.DownloadResult
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.upload.UploadResult
    options:
      show_root_heading: true
      show_source: false

## Programmatic API Functions

These functions are exported from `network_toolkit.api` for direct use.

### Command Execution

::: network_toolkit.api.run.run_commands
    options:
      show_root_heading: true
      show_source: false

### Backup Operations

::: network_toolkit.api.backup.run_backup
    options:
      show_root_heading: true
      show_source: false

### Diff Operations

::: network_toolkit.api.diff.diff_targets
    options:
      show_root_heading: true
      show_source: false

### File Transfer

::: network_toolkit.api.download.download_file
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.upload.upload_file
    options:
      show_root_heading: true
      show_source: false

### Inventory Queries

::: network_toolkit.api.list.get_device_list
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.list.get_group_list
    options:
      show_root_heading: true
      show_source: false

::: network_toolkit.api.list.get_sequence_list
    options:
      show_root_heading: true
      show_source: false

### Parallel Execution

::: network_toolkit.api.execution.execute_parallel
    options:
      show_root_heading: true
      show_source: false
