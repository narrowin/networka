# Backups

Run a configuration backup for a named device or group.

```bash
nw backup config router1
nw backup config office_switches
```

Backup downloads are enabled by default. Use `--no-download` to leave files
on the device, or `--delete-remote` to remove generated files after successful
download.

See which registered platforms implement configuration backup.

```bash
nw platforms list --capability config_backup
```

The device platform determines the backup behavior. See the
[RouterOS guide](vendors/mikrotik/index.md#backups) or
[Cisco guide](vendors/cisco/index.md#backups) for details.
