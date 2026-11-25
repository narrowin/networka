# Platform compatibility

This table applies to Networka 0.2.0 with Scrapli 2.0.4.

| Host | Candidate status |
| --- | --- |
| macOS arm64 | Upstream wheel available. The native CLI, commands, and literal confirmation were exercised on this host. |
| Linux x86-64 and arm64 | Upstream wheels exist for glibc and musl. The release workflow includes an Ubuntu runner. Linux execution awaits verification. |
| Windows with WSL2 | A Linux environment is a candidate installation target. WSL2 execution awaits verification. |
| Native Windows and Intel macOS | No compatible upstream wheel for the current driver. |

The package requires Python 3.15 or later. CI uses Python 3.15. Install OpenSSH to use the system transport and tmux for multi-pane sessions. [Scrapli 2026.11.12 release files](https://pypi.org/project/scrapli/2026.11.12/#files) · [Transport selection](transport.md)

## Inspect connection definitions and capabilities

Run these commands from a clean installation to browse the active Scrapli
catalog and inspect a specific platform.

```bash
nw platforms list
nw platforms info mikrotik_routeros
```

The list separates the operations registry from the active definition names.
The definition source is the packaged Scrapli catalog or the directory selected
by `SCRAPLI_DEFINITIONS_PATH`. An override replaces the packaged catalog for
lookup. Registry filters apply to the operations table.

Platform details show the definition and source selected by the platform name,
any connection alias, registered vendor operations, and applicable sequence names
with their source. For a sequence's commands, run
`nw info <sequence> --vendor <platform>`. The sequence view uses the same default
configuration discovery as the regular inspection commands. A configured sequence
can take precedence over a packaged sequence.

Device qualification depends on the hardware, OS version, and the operation
tested. A definition can be available for a platform with no registered vendor
operations or packaged sequences.
