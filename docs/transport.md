# Transport selection

Networka 0.2.0rc1 uses the Scrapli 2.0.4 implementation via the `scrapli==2026.11.12` distribution. This lets the resolver replace the legacy `scrapli` distribution in the same environment. Use a fresh environment if an early preview installed the separate `scrapli2` distribution.

The driver family remains `scrapli`. The CLI `--transport` option takes precedence over the device's `transport_type` and then `general.default_transport_type`. Set the underlying connection backend with `general.transport` or `overrides.transport` for a device.

| Backend | Configuration and behavior |
| --- | --- |
| `system` (default) | Uses the system OpenSSH executable. `ssh_config_file: true` reads its normal configuration. Set the flag to false to bypass it. |
| `ssh2` | Uses bundled libssh2. Set `ssh_config_file: false` and supply a directly reachable host. Strict mode checks the user's `~/.ssh/known_hosts`. |
| `telnet` | Uses native Telnet. Set the inventory port explicitly, normally 23. |
| Legacy `paramiko`, `asyncssh`, `asynctelnet` | Choose a supported backend for this candidate or use the compatibility line. Paramiko still handles SFTP. |

For CLI SSH sessions with a populated known-hosts file, enable `general.ssh_strict_host_key_checking`. The default value of false disables verification. SFTP uses an independent Paramiko connection and applies the same flag. In strict mode it checks the inventory host and port against `~/.ssh/known_hosts` before sending the password.

`general.timeout` sets the session opening deadline. `general.command_timeout` sets the command deadline. Prompted operations can set their own deadline. An interrupted operation can already have reached the device. Check device state before repeating it.

The candidate uses RouterOS plain-console login and a single carriage return to keep command replies aligned. RouterOS 7.20.6 and 7.25.2 and Cisco IOL 17.18.02 were qualified in disposable labs. Cisco IOS and IOS-XE accept a separate enable secret from `NW_ENABLE_PASSWORD_<DEVICE>` or `NW_ENABLE_PASSWORD_DEFAULT`. The device-specific value takes precedence. Device names use the same uppercase form as `NW_PASSWORD_<DEVICE>`. [Release qualification](development/networka-release-qualification.md)
