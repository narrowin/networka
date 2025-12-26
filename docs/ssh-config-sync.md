# SSH Config Sync

Sync SSH config hosts to YAML inventory in seconds.

## Prerequisites

- An existing SSH config file with Host entries (typically `~/.ssh/config`)
- Networka installed and initialized (`nw config init`)

## Minimal working example

```bash
nw sync ssh-config
```

This uses sensible defaults:
- Input: `~/.ssh/config`
- Output: `<config-dir>/devices/ssh-hosts.yml`

Override when needed:

```bash
nw sync ssh-config ~/.ssh/config.d/routers -o routers.yml
```

**Expected output (first run):**

```
Added 5 hosts: router1, switch1, firewall1, jump-host, dev-server
Wrote 5 devices to /home/user/.config/networka/config/devices/ssh-hosts.yml
```

**Expected output (subsequent run with changes):**

```
Added 1 hosts: new-server
Updated 2 hosts: router1, switch1
No changes (3 hosts unchanged)
Wrote 6 devices to /home/user/.config/networka/config/devices/ssh-hosts.yml
```

## Options reference

| Option | Short | Description |
|--------|-------|-------------|
| `SSH_CONFIG_PATH` | | Path to SSH config file (default: `~/.ssh/config`) |
| `--output PATH` | `-o` | Output YAML inventory file (default: `<config>/devices/ssh-hosts.yml`) |
| `--default-device-type TEXT` | | Default device_type for new hosts (default: `generic`) |
| `--include PATTERN` | | Include hosts matching pattern (can repeat) |
| `--exclude PATTERN` | | Exclude hosts matching pattern (can repeat) |
| `--prune` | | Remove hosts no longer in SSH config |
| `--dry-run` | | Show changes without writing |
| `--verbose` | `-v` | Enable verbose output |

## How syncing works

The sync command performs these operations:

1. **Add new hosts**: Hosts in SSH config but not in inventory are added
2. **Update changed hosts**: Hosts already in inventory are updated if `host`, `user`, or `port` changed in SSH config
3. **Preserve manual edits**: Fields like `device_type`, `tags`, `description` are never overwritten
4. **Remove stale hosts**: With `--prune`, hosts no longer in SSH config are removed (only those originally synced)

### Field handling

The sync tracks these fields from SSH config:

| SSH Config | YAML Inventory | Behavior |
|------------|----------------|----------|
| `HostName` | `host` | Created on add, updated on change |
| `User` | `user` | Created if set, removed if unset in SSH config |
| `Port` | `port` | Created if set, removed if unset in SSH config |

All other fields in the YAML inventory are preserved across syncs.

### The _ssh_config_source marker

Each synced host receives a `_ssh_config_source` marker field containing the SSH config Host name. This marker:

- Identifies hosts that were synced from SSH config (vs manually created)
- Ensures only SSH-synced hosts are updated or pruned on subsequent runs
- Allows manual inventory entries to coexist safely with synced entries

Example output:

```yaml
router1:
  host: 192.168.1.1
  device_type: generic
  user: admin
  port: 22
  _ssh_config_source: router1
```

Hosts without this marker are never modified by subsequent syncs.

## Filtering hosts

Use `--include` and `--exclude` to filter which hosts are synced. Both accept fnmatch-style patterns.

**Include only hosts matching a pattern:**

```bash
nw sync ssh-config ~/.ssh/config -o devices.yml --include "router*" --include "switch*"
```

**Exclude specific hosts:**

```bash
nw sync ssh-config ~/.ssh/config -o devices.yml --exclude "*.local" --exclude "jump-*"
```

**Combine include and exclude:**

```bash
nw sync ssh-config ~/.ssh/config -o devices.yml --include "prod-*" --exclude "*-test"
```

Include is applied first, then exclude filters the result.

## Dry-run mode

Preview changes without writing to the inventory file:

```bash
nw sync ssh-config ~/.ssh/config -o devices.yml --dry-run
```

Output:

```
[DRY RUN] Added 3 hosts: new-server1, new-server2, new-server3
[DRY RUN] Updated 1 hosts: router1
[DRY RUN] No changes written
```

## Verbose mode

Enable debug logging to see detailed parsing information:

```bash
nw sync ssh-config ~/.ssh/config -o devices.yml --verbose
```

## Error handling

### Include directives not supported

SSH config files with `Include` directives cannot be parsed directly:

```
Error: SSH config files with 'Include' directives are not currently supported.
Please flatten your SSH config or specify the included file directly.
```

**Solution**: Either flatten your SSH config or point directly at an included file:

```bash
nw sync ssh-config ~/.ssh/config.d/routers -o routers.yml
```

### Invalid YAML in inventory file

If the output file contains invalid YAML:

```
Error: Invalid YAML in inventory file: /path/to/devices.yml
```

**Solution**: Fix the YAML syntax in the inventory file or delete it to start fresh.

### Permission errors

If the SSH config or inventory file cannot be read/written:

```
Error: Permission denied reading SSH config: ~/.ssh/config
```

**Solution**: Check file permissions. SSH config should be readable (typically mode 600 or 644).

## Integration with Networka workflow

### Preserving manual edits

Add device-specific configuration after syncing:

```yaml
# devices/ssh-hosts.yml
router1:
  host: 192.168.1.1
  device_type: mikrotik_routeros    # Changed from generic
  user: admin
  port: 22
  tags: [edge, critical]            # Added manually
  description: Main edge router     # Added manually
  _ssh_config_source: router1
```

These manual additions are preserved on subsequent syncs. Only `host`, `user`, and `port` are updated from SSH config.

### Combining with other inventory sources

SSH-synced inventory can coexist with:

- Manually created device files
- Nornir/Containerlab inventory (via `inventory.source: nornir_simple`)
- CSV imports

Networka merges all sources; later files override earlier ones by device name.

### Suggested workflow

1. Initial sync from SSH config
2. Edit device_type for each host (change from `generic` to `mikrotik_routeros`, `cisco_iosxe`, etc.)
3. Add tags and descriptions as needed
4. Re-run sync periodically to pick up new hosts or connection changes
5. Use `--prune` when you want to remove hosts deleted from SSH config

## Troubleshooting

### Hosts not appearing in inventory

1. Check the host entry has a valid `HostName` directive
2. Wildcard patterns (`Host *`, `Host *.example.com`) are skipped
3. Verify the host is not excluded by an `--exclude` pattern
4. Host names must contain only letters, numbers, dots, hyphens, and underscores

### Updates not detected

The sync only updates hosts with the `_ssh_config_source` marker. Manually created entries are never modified. If a host was manually created with the same name, the sync will skip it.

### Pruned hosts reappearing

Ensure you run with `--prune` consistently. Without `--prune`, hosts removed from SSH config remain in the inventory.
