# IP address support

Use an IP address to run commands before adding a device to inventory. A raw IP
needs a platform even if the same address appears in inventory. To use the
platform and other settings from inventory, target the configured device name.

## Run a command without configuration

For a RouterOS device, replace the example address with your device's address.
The interactive prompt supplies its access details.

```bash
nw run 192.0.2.10 "/system/identity/print" --platform mikrotik_routeros --interactive-auth
```

You can also inspect and run a packaged sequence.

```bash
nw info system_info --vendor mikrotik_routeros
nw run 192.0.2.10 system_info --platform mikrotik_routeros --interactive-auth
```

The first command shows the selected commands and their source. The second
runs them on the device. This interactive path works without a configuration
file for a target made up entirely of IP addresses.

## Choose a platform

Use `nw platforms list` for the active Scrapli definition names and
`nw platforms info mikrotik_routeros` for the source, sequences, and available
vendor operations. Installed definitions describe how to communicate with a
platform. Device qualification depends on the model, OS version, and operation.

Supply the network OS with `--platform`. Scrapli loads the selected definition
by name. It has no device-platform detection API. The existing aliases
`linux` and `generic` select Scrapli's generic `default` definition for shell
prompts. Use the actual platform name when you need its prompts or sequences.

## Multiple targets and connection options

A comma-separated list of raw IPs uses the same platform for every address.

```bash
nw run 192.0.2.10,192.0.2.11 system_info --platform mikrotik_routeros --interactive-auth
```

Use a separate invocation for configured names. The ad hoc address list
requires every target to be an IP. Named devices and groups can share an
invocation and use their configured `device_type`.

Supply credentials through your configuration or
[environment variables](environment-variables.md), or prompt with
`--interactive-auth`. Add `--port 2222` for a non-default port. The
[transport guide](transport.md) explains SSH backend and host-key settings.

For interactive SSH panes, `nw cli` uses OpenSSH and loads configuration.
For example, `nw cli 192.0.2.10 --platform mikrotik_routeros --auth interactive`.
See [tmux CLI sessions](tmux-ssh.md).

## Inspect and troubleshoot

If an IP target cannot resolve its platform, use `nw platforms list` and pass
an available name with `--platform`. If the definition directory is an
override, only definitions in that directory are available by name.

`nw info` inspects configured names and sequences. For Python usage, see
[ad hoc targets](library/adhoc-targets.md).
