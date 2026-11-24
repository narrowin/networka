# Networka release qualification

24 November 2026

## Packaging and infrastructure

| Problem | Fix | Proof |
| --- | --- | --- |
| A fresh 0.1.13 install could resolve the rewritten Scrapli package and a libtmux version that removed APIs used by the CLI. | Built 0.1.14 from the published tag and constrained the dependencies at the package boundary. Kept the maintained branch on the current tmux API and moved Scrapli 2 to a separate candidate. | Clean wheel and source installs for all three versions started `nw` and passed dependency checks on macOS arm64 and Linux arm64 and x86-64. The candidate loaded its native library on both Linux architectures. |
| Release routing treated the `a` in `refs/tags/` as a prerelease marker. Local and CI environments could also select different Python interpreters. | Parse the version once using PEP 440. Install each build artifact independently before publication. Use uv 0.13.9 and explicitly select each CI interpreter. Use the same preflight when preparing a maintenance release. | Canonical stable and prerelease routing checks and the 0.1.14 preflight and dry run passed. The maintained and candidate suites passed on Python 3.11–3.15. The dry run uses the checked preflight marker for the exact release commit. |

## File transfer and pooled sessions

| Problem | Fix | Proof |
| --- | --- | --- |
| Upload verification put the remote path in the name of a local temporary file, so upload into a directory succeeded but returned failure after repeated verification attempts. | Use a generated local name and pass the original remote path directly to the existing download and SHA-256 checks. | An identical nested-path upload returned failure before the fix. All three rebuilt wheels verified the checksum and returned the original 256 bytes from the disposable Linux server. |
| SFTP ignored strict SSH host-key checking, and the legacy Paramiko CLI adapter did not request the known-hosts file. | Load the known key before SFTP authentication and verify the negotiated key for the configured host and port. Enable the legacy adapter’s known-hosts lookup in strict mode. | Each rebuilt wheel authenticated with the trusted key. SFTP rejected both a missing and mismatched key. The legacy CLI connected via Paramiko and the candidate via native SSH2 in strict mode. |
| Requested removal after SFTP download used a RouterOS command and could still report success when removal failed. | Remove the same remote path through the already-authenticated SFTP session and propagate removal errors. | All three wheels downloaded the same bytes, removed the requested remote file, and confirmed its absence through a second SFTP download. |
| The pool could replay a command when the device had already executed it. Transfer context managers could also attempt to yield a second session after an operation failed. | Limit retries to connection setup. Run the command or yield the connected session after the retry block. | An actual pooled command that wrote one byte and closed its shell produced two bytes before the fix and one after it. The fixed call returned the unconfirmed result. Eleven existing upload CLI cases now exercise the current command and strict success or failure expectations. |

## Scrapli 2 compatibility and release status

| Problem | Fix | Proof |
| --- | --- | --- |
| Scrapli 2 rewrote command execution, transport configuration, and prompted input. RouterOS needs console settings that the native wheel omitted. | Map the existing transport interface to Scrapli 2.0.4, preserve the RouterOS login suffix and line ending, and keep Paramiko for SFTP. Report interrupted confirmations as unconfirmed. | In a disposable RouterOS 7.20.6 emulator, all three builds returned the expected identity and version over a reused SSH session. A native session answered a literal prompt against a local shell. |
| The native candidate still lacks evidence for Cisco privilege transitions, WSL2, and device restart confirmations. Upstream supplies no wheel for Intel macOS or native Windows. | Release 0.1.14 on the verified legacy driver. Keep the refreshed 0.2 and native 0.3 builds available for further qualification. | 0.1.14 passed 891 tests with 39 skipped on Python 3.13. Both development lines passed 1,134 tests with 31 skipped per Python version from 3.11 through 3.15. Production publication and hosted CI remain pending. |

The artifacts are in `dist/rebirth` in the local checkout. [Scrapli 2.0.4 release files](https://pypi.org/project/scrapli2/2.0.4/#files)
