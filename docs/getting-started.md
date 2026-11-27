# Installation

Networka requires Python 3.15 or later. Use Linux x86-64 or ARM64, or Apple
Silicon macOS. See [platform compatibility](platform-compatibility.md).

The examples on this page use the current checkout. Install it in an
isolated tool environment from the checkout directory.

```bash
uv tool install --python 3.15 .
nw --version
```

To use the project environment instead, run `uv sync --locked` and prefix
the examples with `uv run --locked`.

For the published release, use `uv tool install --python 3.15 networka`.
Use the installed release's `nw --help` to check its available commands.

## Run your first sequence

Inspect the active definitions and the packaged RouterOS sequence.

```bash
nw platforms list
nw info system_info --vendor mikrotik_routeros
```

Replace the example IP with a RouterOS device you can access. Enter the
username and password when prompted.

```bash
nw run 192.0.2.10 system_info --platform mikrotik_routeros --interactive-auth
```

The inspection shows the commands and source. The run displays their output.
Learn more about [IP targets](ip-address-support.md) and [stored results](results.md).

## Add inventory for recurring work

Initialize a modular configuration to reuse named devices or groups.

```bash
nw config init
```

Within the configuration directory, edit the generated `router1`
entry under `devices/`. If you started with an empty configuration,
add it in a file such as `devices/router1.yml`.

```yaml
devices:
  router1:
    host: 192.0.2.10
    device_type: mikrotik_routeros
```

Then run the sequence by name. The inventory supplies the platform.

```bash
nw run router1 system_info --interactive-auth
```

See [configuration](configuration.md) for file locations and inventory sources
and [environment variables](environment-variables.md) for setting credentials.

## Next steps

- [Run commands and sequences](running-commands.md)
- [Save results and compare with saved output](results.md)
- [Open interactive SSH panes with tmux](tmux-ssh.md)
- [Troubleshoot installation or connections](troubleshooting.md)
