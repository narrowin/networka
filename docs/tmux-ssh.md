# Cross-Platform SSH fanout

This adds a `nw ssh` command that opens SSH sessions to multiple devices simultaneously. The implementation adapts to your platform capabilities.

## Platform Support

### Full tmux-based fanout (Recommended)
**Platforms:** Linux, macOS, Windows with WSL
- Opens tmux session with one pane per device
- Synchronized typing across all panes
- Native tmux navigation and controls

### Sequential SSH fallback
**Platforms:** Windows (native), any system without tmux
- Opens SSH connections one by one
- No synchronized typing
- Basic cross-platform compatibility

## Requirements

### For tmux-based fanout:
- tmux installed and available
- libtmux Python package (install with `uv add libtmux` or `pip install libtmux`)
- SSH client (OpenSSH recommended)
- sshpass for password authentication (Linux/macOS: `apt install sshpass` or `brew install hudochenkov/sshpass/sshpass`)

### For sequential fallback:
- Any SSH client (OpenSSH, PuTTY plink, etc.)
- libtmux package still required (but tmux server not needed)

### Windows-specific notes:
- **Option 1 (Recommended):** Use WSL2 with tmux for full functionality
- **Option 2:** Native Windows with sequential SSH fallback
- **SSH clients supported:** Windows OpenSSH (Win10+), PuTTY plink, Git Bash SSH

## Usage
- Single device: `nw ssh sw-acc1`
- Group: `nw ssh office_switches`
- Custom layout: `nw ssh lab_devices --layout even-vertical`
- Name session/window: `nw ssh core --session-name ops --window-name core-routers`
- Disable synchronized typing: `nw ssh lab_devices --no-sync`

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
