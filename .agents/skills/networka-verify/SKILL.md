---
name: networka-verify
description: Verify changed Networka code, CLI or configuration behavior, or packages with existing tests, the offline nw walkthrough, and clean artifact installs.
---

# Verify Networka changes

Read [AGENTS.md](../../AGENTS.md) and the relevant checks in the
[development guide](../../../docs/development.md). Identify the changed
behavior and files from the request or the diff. A live run needs a named
target and explicitly approved operations.

- Select existing tests that assert the changed behavior. For documentation
  edits, build MkDocs with strict checking. Regenerate CLI reference when
  command declarations or help change.
- For CLI and configuration changes, run the offline walkthrough and check the
  actual status, output, and source paths that relate to the change. For
  packaging changes, run the clean install check and record the wheel and
  source archive hashes.
- Use the authorized lab procedure only when the request covers live access
  to the exact target and operations. Inspect identity, OS version, and the
  relevant command output. With no authorized target, use applicable local
  checks and report any live verification still needed.
- Review the diff and run `git diff --check`. Report the commands and observed
  results for each check, including Python version, failed or skipped cases,
  and layers left untested. Claims about device behavior require an authorized
  device result.
