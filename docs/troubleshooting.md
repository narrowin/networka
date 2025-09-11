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
- Check files are in the correct directories under `config/`.
- For CSV, ensure headers match the documented schema.
- See: Configuration (CSV).

## Output formatting and results
- Use `--output-mode` to adjust styling.
- Use `--store-results` and `--results-format` to save outputs.
- See: Output modes, Results.
