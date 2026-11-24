# Transport selection

Networka 0.3.0.dev0 uses the `scrapli2==2.0.4` distribution. It shares the `scrapli` import name with the legacy distribution. Use a separate uv environment for each version.

The driver family remains `scrapli`. The CLI `--transport` option takes precedence over the device's `transport_type` and then `general.default_transport_type`. Set the underlying connection backend with `general.transport` or `overrides.transport` for a device.

| Backend | Configuration and behavior |
| --- | --- |
| `system` (default) | Uses the system OpenSSH executable. `ssh_config_file: true` reads its normal configuration. Set the flag to false to bypass it. |
| `ssh2` | Uses bundled libssh2. Set `ssh_config_file: false` and supply a directly reachable host. Strict mode checks the user's `~/.ssh/known_hosts`. |
| `telnet` | Uses native Telnet. Set the inventory port explicitly, normally 23. |
| Legacy `paramiko`, `asyncssh`, `asynctelnet` | Choose a supported backend for this candidate or use the compatibility line. Paramiko still handles SFTP. |

For CLI SSH sessions with a populated known-hosts file, enable `general.ssh_strict_host_key_checking`. The default value of false disables verification. SFTP uses an independent Paramiko connection and applies the same flag. In strict mode it checks the inventory host and port against `~/.ssh/known_hosts` before sending the password.

`general.timeout` sets the session opening deadline. `general.command_timeout` sets the command deadline. Prompted operations can set their own deadline. An interrupted operation can already have reached the device. Check device state before repeating it.

The local qualification used a shell over a pseudo-terminal. RouterOS login options, command echoes, Cisco privilege transitions, and SFTP still need comparison on representative devices. [Upgrade report](development/networka-upgrade-report-2026-11-24.md)
