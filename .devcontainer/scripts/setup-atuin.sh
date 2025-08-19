#!/bin/bash
set -euo pipefail

echo "=== Setting up atuin configuration ==="

# Create atuin directories if they don't exist
mkdir -p ~/.config/atuin
mkdir -p ~/.local/share/atuin

# Initialize atuin database if it doesn't exist
if [ ! -f ~/.local/share/atuin/history.db ]; then
    echo "Initializing atuin database..."
    atuin import auto
    echo "✓ Atuin database initialized"
else
    echo "✓ Atuin database already exists"
fi

# Add atuin to bashrc if not already present
if ! grep -q "atuin init bash" ~/.bashrc; then
    echo "Adding atuin integration to ~/.bashrc..."
    echo '' >> ~/.bashrc
    echo '# Atuin shell history' >> ~/.bashrc
    echo 'eval "$(atuin init bash --disable-up-arrow)"' >> ~/.bashrc
    echo "✓ Atuin bash integration added"
else
    echo "✓ Atuin bash integration already configured"
fi

# Create atuin configuration file with development-friendly settings
cat > ~/.config/atuin/config.toml << 'EOF'
# Atuin configuration for development environment

## where to store your database, default is your system data directory
## linux: ~/.local/share/atuin/history.db
## macOS: ~/Library/Application Support/atuin/history.db
## Windows: %USERPROFILE%\AppData\Roaming\atuin\history.db
# db_path = "~/.local/share/atuin/history.db"

## where to store your encryption key, default is your system data directory
# key_path = "~/.local/share/atuin/key"

## where to store your auth session token, default is your system data directory
# session_path = "~/.local/share/atuin/session"

## date format used, either "us" or "iso"
dialect = "iso"

## enable or disable automatic sync
auto_sync = false

## enable or disable automatic update checks
update_check = false

## address of the sync server
sync_address = "https://api.atuin.sh"

## how often to sync history. note that this is only triggered when a command
## is ran, so sync intervals may be longer
## set it to 0 to sync after every command
sync_frequency = "1h"

## which search mode to use
## possible values: prefix, fulltext, fuzzy, skim
search_mode = "fuzzy"

## which filter mode to use
## possible values: global, host, session, directory
filter_mode = "global"

## which style to use
## possible values: auto, full, compact
style = "auto"

## the maximum number of lines to show for the interface
max_preview_height = 4

## whether or not to show the help text
show_help = true

## whether or not to show tabs
show_tabs = true

## exit the interface immediately when a command is selected
exit_mode = "return-query"

## prevent commands matching any of these regexes from being written to history.
## Note that these regular expressions are unanchored, i.e. if they don't start
## with ^ or end with $, they'll match anywhere in the command.
## For details on the supported regular expression syntax, see
## https://docs.rs/regex/latest/regex/#syntax
history_filter = [
    "^secret-cmd",
    "^password",
    "^passwd",
    "export .*PASSWORD.*",
    "export .*SECRET.*",
    "export .*KEY.*",
    "export .*TOKEN.*"
]

## prevent commands run with cwd matching any of these regexes from being written
## to history. Note that these regular expressions are unanchored, i.e. if they don't
## start with ^ or end with $, they'll match anywhere in the command.
cwd_filter = []

## configure whether or not to record the exit code of a command
record_exit = true

## Set this to true and Atuin will minimize motion in the UI - timers will not update live, etc.
## Alternatively, set env NO_MOTION=true
static_ui = false

## Defaults to true. This matches the FZF behavior, but can be turned off if you find it jarring.
invert_ui = true

## Defaults to 'name'. Can also be 'alias'.
## If set to 'alias', the history list will show the alias if one was used for a command.
word_jump_mode = "name"

## characters that count as a part of a word
word_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"

## number of context lines to show when scrolling by pages
scroll_context_lines = 1

## use ctrl instead of alt as the shortcut modifier key for numerical UI shortcuts
## alt-0 .. alt-9
ctrl_n_shortcuts = false

## default timezone to use when displaying time
## either "system" for system timezone, or use something like "US/Eastern"
timezone = "system"

## Cursor style in atuin query
## Defaults to "blink-block"
## Currently: "blink-block", "blink-underscore", "steady-block", "steady-underscore"
cursor_style = "blink-block"

## possible values: emacs, vi
keymap_mode = "emacs"

## Cursor position when exiting atuin
## Defaults to "maintain" to maintain the cursor position
## Also supports "end" to move the cursor to the end of the line
keymap_cursor = "end"

## Minimum delay between activity records in seconds. Defaults to 1.
activity_record_min_delay = 1

## Activity record enabled? Defaults to false.
activity_record_enabled = false

## Network connect timeout in seconds. Defaults to 5.
network_connect_timeout = 5

## Network request timeout in seconds. Defaults to 5.
network_timeout = 5

## Local network (non-sync) timeout in seconds. Defaults to 0.5.
local_timeout = 0.5

## Set this to true and Atuin will prefer to use data from the locally-stored database.
prefers_reduced_motion = false

## Set this to true to enable kitty keyboard protocol support
enter_accept = true

EOF

echo "✓ Atuin configuration created at ~/.config/atuin/config.toml"

# Initialize atuin database if it doesn't exist
if [ ! -f ~/.local/share/atuin/history.db ]; then
    echo "Initializing atuin database..."
    atuin import auto
    echo "✓ Atuin database initialized"
else
    echo "✓ Atuin database already exists"
fi

echo ""
echo "Atuin setup complete! Key features:"
echo "  - Fuzzy search mode enabled"
echo "  - Auto-sync disabled (local-only)"
echo "  - Password/secret filtering enabled"
echo "  - Exit codes recorded"
echo ""
echo "Usage:"
echo "  - Ctrl+R: Search history"
echo "  - Up/Down: Navigate results"
echo "  - Tab: View more details"
echo "  - Enter: Execute command"
echo ""
echo "Commands:"
echo "  - 'atuin search <query>': Search from command line"
echo "  - 'atuin stats': View usage statistics"
echo "  - 'atuin history list': List recent commands"
