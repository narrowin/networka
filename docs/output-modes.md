# Output modes

Use `--output-mode` on commands that expose it. Set
`general.output_mode` in `config.yml` to `default`, `light`, `dark`,
`no-color`, or `raw` for a shared default.

| Mode | Output |
| --- | --- |
| `default` | Adaptive terminal styling |
| `light` | Colors for light terminals |
| `dark` | Colors for dark terminals |
| `no-color` | Readable output without ANSI colors |
| `raw` | Minimal decoration for scripts |
| `json` | JSON status records via the CLI option or environment on supported commands |

Output mode selection follows this order.

1. The command's `--output-mode` option.
2. A nonempty `NO_COLOR`.
3. `NW_OUTPUT_MODE`.
4. `general.output_mode`.

Redirected styled output is plain by default. `FORCE_COLOR` requests ANSI
color in redirected styled output.

```bash
nw info router1 --output-mode raw
nw run router1 system_info --output-mode json
```

In a run, JSON status records can appear alongside plain device output.
Set `general.results_format` to choose the format of
[stored result files](results.md).
