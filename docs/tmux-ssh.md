# tmux-based SSH fanout (prototype)

This adds a lean `netkit ssh` command that opens a tmux session and starts SSH in one pane per device. It relies on your local SSH config/keys and tmux.

## Requirements
- Linux/macOS with tmux installed
- libtmux Python package (install with `uv add libtmux` or `pip install libtmux`)
- SSH keys/agent recommended.
- sshpass is required when using password authentication (either `--auth password` or when `--auth auto` detects a password). Install with your package manager, e.g. `apt install sshpass` or `brew install hudochenkov/sshpass/sshpass`.

## Usage
- Single device: `netkit ssh sw-acc1`
- Group: `netkit ssh office_switches`
- Custom layout: `netkit ssh lab_devices --layout even-vertical`
- Name session/window: `netkit ssh core --session-name ops --window-name core-routers`
- Disable synchronized typing: `netkit ssh lab_devices --no-sync`

By default, panes are synchronized so your keystrokes go to all panes. Toggle with `--sync/--no-sync`.

Authentication modes:
- `--auth auto` (default): uses password auth via sshpass if a password is available from env/config; otherwise uses key-based SSH.
- `--auth key`: always uses your SSH keys/agent.
- `--auth password`: forces password auth (requires sshpass).
- `--auth interactive`: lets ssh prompt in each pane.

## Layouts
Supported tmux layouts:
- tiled (default)
- even-horizontal
- even-vertical
- main-horizontal
- main-vertical

## Keyboard shortcuts (tmux defaults)
- Prefix: Ctrl-b
- Pane navigation: Prefix + Arrow keys
- Split pane: Prefix + % (vertical), Prefix + " (horizontal)
- Cycle layouts: Prefix + Space
- Toggle synchronize-panes: Prefix + : then `set synchronize-panes on|off` (we set it initially if `--sync`)
- Detach: Ctrl-b then d

## Send a command to all panes
With synchronize-panes enabled, type the command once and press Enter. All panes receive it.

## Security note on password authentication
When password auth is used, the password is passed to `sshpass` and may appear in process lists. Prefer SSH keys for security. If you cannot use keys, consider interactive auth (`--auth interactive`) to avoid passing passwords via arguments.

Python-only alternative: We could embed an SSH client (e.g., Paramiko) to avoid `sshpass`, but then interactive TTY behavior and tmux integration get more complex. For now we keep it lean by delegating to the system `ssh`.

## tmuxp integration
This prototype keeps it slim with libtmux directly. In future we can accept a `--tmuxp` YAML to load complex layouts via tmuxp (https://tmuxp.git-pull.com/). For now, built-ins cover common needs without extra files.
