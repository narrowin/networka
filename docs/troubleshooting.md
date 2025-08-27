# Troubleshooting

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
