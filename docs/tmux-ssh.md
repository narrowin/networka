# tmux CLI sessions

`nw cli` opens one interactive OpenSSH pane per selected device. It uses
the devices and groups in your [configuration](configuration.md).

## Platform Support

Install Networka on a [compatible host](platform-compatibility.md). If
tmux fanout is unavailable and Networka finds a supported SSH client, the
command can open sequential sessions.

## Requirements

- OpenSSH and tmux on your PATH for multi-pane sessions.
- Networka includes the Python libtmux dependency.
- Use sshpass when you want automatic password entry. OpenSSH can also prompt
  in each pane.

## Usage

- Single device: `nw cli sw-acc1`
- Group: `nw cli office_switches`
- Custom layout: `nw cli lab_devices --layout even-vertical`
- Name session/window: `nw cli core --session-name ops --window-name core-routers`
- Disable synchronized typing: `nw cli lab_devices --no-sync`

**Synchronized typing is ENABLED by default** - your keystrokes are sent to all panes simultaneously. This is perfect for running the same commands across multiple devices. Use `--no-sync` to disable at startup.

## Synchronization Control

### At startup:

- `nw cli devices` - sync enabled (default)
- `nw cli devices --no-sync` - start with sync disabled

### Toggle during session:

**Quick toggle: Press Ctrl+b, t** - This instantly toggles sync on/off

**Manual toggle:**

1. Press Ctrl+b : (colon) to enter tmux command mode
2. Type `set synchronize-panes on` to enable or `set synchronize-panes off` to disable
3. Press Enter to execute

**Visual indicator:** When sync is enabled, all panes show a red border.

**Mouse support:** Click any pane to focus it individually.

Authentication modes:

- `--auth key-first` is the default. OpenSSH tries public keys before passwords.
  Networka can supply an available password through sshpass.
- `--auth key` leaves authentication to OpenSSH without automatic password entry.
- `--auth password` supplies a configured password through sshpass.
- `--auth interactive` lets OpenSSH prompt in each pane.

## Layouts

Supported tmux layouts:

- tiled (default)
- even-horizontal
- even-vertical
- main-horizontal
- main-vertical

## Keyboard shortcuts

- **Ctrl+b, z:** Zoom/unzoom focused pane (automatically exits/enters sync mode)
- **Ctrl+b + Arrow keys:** Navigate between panes
- **Ctrl+b, d:** Detach from session
- **Click any pane:** Focus that pane
- **Ctrl+b, Space:** Cycle through layouts

**Zoom behavior:** When you zoom a pane (Ctrl+b, z), it maximizes that pane and automatically exits sync mode so you can work on just that device. Press Ctrl+b, z again to unzoom and return to sync mode across all panes.

**Manual sync toggle:** Ctrl+b : then type `set synchronize-panes on` or `off` and press Enter

## Send a command to all panes

With synchronize-panes enabled (default), type any command once and press Enter - it will be sent to ALL connected devices simultaneously. This is extremely powerful for:

- Running the same configuration command across multiple devices
- Checking status on all devices at once
- Performing batch operations

**Example:** Type `/system identity print` and press Enter - this will execute on all MikroTik devices in all panes at once.

**Safety tip:** Be careful with destructive commands when sync is enabled! Consider disabling sync (`Ctrl-b : set synchronize-panes off`) for device-specific operations.

## Security note on password authentication

Networka supplies passwords to sshpass through a private pipe. Passing
`--password` puts the value on the command line. Use the
[credential configuration](environment-variables.md) or an interactive
prompt for password authentication.
