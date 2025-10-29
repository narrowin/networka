# Results

Networka can store command results under a timestamped directory when result capture is enabled.

- Root directory: `general.results_dir` (default: `/tmp/results`)
- Auto-created per run: `YYYYMMDD_HHMMSS/`
- Storage toggles on with `--store-results` or by setting `general.store_results: true`

Supported formats come from the configuration value `general.results_format` (`txt`, `json`, or `yaml`).

Examples:

```bash
nw run sw-acc1 health_check --store-results
nw run sw-acc1 system_info --store-results --results-dir ./maintenance-2025-08
nw run group1 check --store-results
```

Config snippet:

```yaml
general:
  store_results: true
  results_dir: ./results
  results_format: json
```

Notes:

- Filenames and subfolders are derived from device/group and command/sequence names.
- Set `general.results_format` to control serialization.
- Results are safe to check into version control if they don't contain secrets.
