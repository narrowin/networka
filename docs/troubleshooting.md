# Troubleshooting

## PATH: 'nw' not found

- Check: `command -v nw` (Linux/macOS) or `where nw` (Windows)
- If using pipx: ensure PATH is set, then reload shell
	```bash
	pipx ensurepath
	exec $SHELL
	```
- Linux/macOS: add user bin to PATH if needed
	```bash
	echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
	exec $SHELL
	```
- Windows (native, best-effort): prefer WSL2; if native, run `pipx ensurepath` and restart the terminal

## Authentication and credentials
- Ensure `NW_USER_DEFAULT` and `NW_PASSWORD_DEFAULT` are set, or use a `.env` file.
- Device-specific overrides: `NW_{DEVICE}_USER`, `NW_{DEVICE}_PASSWORD`.
- See: Environment variables, Interactive credentials.

## SSH host key verification failures

**Default behavior: BALANCED** - Networka uses `accept-new` mode by default, which automatically accepts new host keys but verifies existing ones. This provides security against MITM attacks on known hosts while allowing easy onboarding of new devices.

If you see "Host key verification failed" errors (existing key changed):

### Option 1: Fix the host key (RECOMMENDED)

Clear the old key and accept the new one:

```bash
ssh-keygen -R <hostname_or_ip>
# Then connect again - new key will be automatically accepted
```

### Option 2: Completely disable verification per-command (INSECURE - lab only)

```bash
nw run router1 '/system/identity/print' --no-strict-host-key-checking
nw cli router1 --no-strict-host-key-checking
```

### Option 3: Enable strict mode globally (maximum security)

```yaml
# ~/.config/networka/config.yml
general:
  ssh_strict_host_key_checking: true  # Fail on any unknown/changed key
```

**Configuration precedence:**

- **Default**: `accept-new` mode (accept new keys, verify existing ones)
- **Config file**: `ssh_strict_host_key_checking: false` = accept-new, `true` = strict
- **CLI override**: `--no-strict-host-key-checking` = completely disable all verification
- CLI flags take precedence over configuration file settings

## Timeouts and connectivity

- Verify device is reachable (ping/ssh).
- Increase `general.timeout` in config.
- Check `device_type` matches the platform.
- See: Transport, Platform compatibility.

## Windows notes

- Prefer WSL2 (Ubuntu) for Scrapli-based transport.
- Native Windows may work but is best-effort.
- See: Platform compatibility.

## Configuration loading

- Check files are in the correct directories under `~/.config/networka/`.
- For CSV, ensure headers match the documented schema.
- See: Configuration (CSV).

## Output formatting and results

- Use `--output-mode` to adjust styling.
- Use `--store-results` and `--results-format` to save outputs.
- See: Output modes, Results.
