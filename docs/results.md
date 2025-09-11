# Results

Networka stores command results under a timestamped directory by default.

- Root directory: `general.results_dir` (default: `./results`)
- Auto-created per run: `YYYYMMDD_HHMMSS/`
- Supports multiple formats when `--store-results` is used

Examples:

```bash
nw run sw-acc1 health_check --store-results
nw run sw-acc1 system_info --store-results --results-format json
nw run group1 check --results-dir ./maintenance-2025-08
```

Config snippet:

```yaml
general:
  results_dir: ./results
```

Notes:
- Filenames and subfolders are derived from device/group and command/sequence names.
- Use `--results-format` to control serialization (e.g., json, text).
- Results are safe to check into version control if they don't contain secrets.
