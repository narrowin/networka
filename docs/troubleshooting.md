# Troubleshooting

## PATH: 'nw' not found

Use `command -v nw` to see whether your shell can find the command. With a uv
tool installation, run `uv tool update-shell` and open a new shell. If you
installed from the checkout with `uv sync --locked`, use
`uv run --locked nw --help` in that checkout.

## Authentication and credentials

Set `NW_USER_DEFAULT` and `NW_PASSWORD_DEFAULT`, or prompt on `nw run` with
`--interactive-auth`. Use `NW_USER_<DEVICE>` and `NW_PASSWORD_<DEVICE>` for
per-device values. See [environment variables](environment-variables.md) for
precedence and naming.

## SSH host key verification failures

Host-key checking defaults to disabled. Enable
`general.ssh_strict_host_key_checking` to check keys. With that setting,
`nw cli` uses OpenSSH's `accept-new` mode, while the command and SFTP
connections use their own verification paths. See
[transport selection](transport.md).

If a previously known key has changed, verify the replacement fingerprint
independently before updating the corresponding known-hosts entry.

## Timeouts and connectivity

Check that the host and port are reachable, then inspect the chosen platform.

```bash
nw info router1 --trace
nw platforms info mikrotik_routeros
```

Use `general.timeout` for connection opening and `general.command_timeout`
for command execution. See [transport selection](transport.md).

## Windows notes

The current native driver wheels cover Linux and Apple Silicon macOS.
WSL2 remains unverified. See [platform compatibility](platform-compatibility.md).

## Configuration loading

Point the command's `--config` at the directory containing `config.yml` or
at that file. Use `nw config validate` for the default configuration. See
[configuration](configuration.md) for file layout and CSV columns.

## Output formatting and results

Use `--output-mode` to control display and `--store-results` to capture
outputs. Set `general.results_format` in `config.yml` to choose the stored
format. [Output modes](output-modes.md) · [Results](results.md)
