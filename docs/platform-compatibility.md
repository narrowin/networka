# Platform compatibility

This table applies to Networka 0.3.0.dev0 with Scrapli 2.0.4.

| Host | Candidate status |
| --- | --- |
| macOS arm64 | Upstream wheel available. The native CLI, commands, and literal confirmation were exercised on this host. |
| Linux x86-64 and arm64 | Upstream wheels exist for glibc and musl. The release workflow includes an Ubuntu runner. Linux execution awaits verification. |
| Windows with WSL2 | A Linux environment is a candidate installation target. WSL2 execution awaits verification. |
| Native Windows and Intel macOS | No compatible upstream wheel. Keep the legacy Networka environment for these hosts. |

The package requires Python 3.11 or later. The configured CI matrix covers Python 3.11 through 3.15. Install OpenSSH to use the system transport and tmux for multi-pane sessions. [Scrapli 2.0.4 release files](https://pypi.org/project/scrapli2/2.0.4/#files) · [Transport selection](transport.md)
