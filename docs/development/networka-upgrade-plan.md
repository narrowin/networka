# Networka upgrade plan

The [upgrade report](networka-upgrade-report-2026-11-24.md) records the dependency trials, alternatives, and compatibility risks. Each stage below has a separate acceptance check.

1. **Repair the published line.** Prepare 0.1.14 from the 0.1.13 tag. Constrain the legacy driver and tmux API, correct stable and prerelease routing, and install the resulting wheel and sdist in fresh environments.
2. **Refresh the maintained line.** Unify uv, run the actual Python matrix, upgrade the lock and developer tools, modernize tmux, restore the typing marker, and repair the existing inventory and lab checks. Keep the legacy transport available on this line. Verify the CLI, SDK, existing suite, docs, types, and built packages.
3. **Build the Scrapli 2 candidate.** Use a separate branch and environment for the native driver. Port construction, command and confirmation handling, SSH settings, timeouts, and session lifecycle. Check wheel installation, available definitions, and existing CLI and SDK behavior.
4. **Review release readiness.** Compare read-only command results on approved lab devices, record uncovered platforms and operations, and retain the compatibility release for rollback. Tagging, pushing, publishing, and device changes require operator approval.
