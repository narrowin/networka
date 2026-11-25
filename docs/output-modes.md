# Output modes

Control colors and formatting globally with `general.output_mode`.

- default: Adaptive styling (Rich defaults)
- light: Colors optimized for light terminals
- dark: Colors optimized for dark terminals
- no-color: Structured output without ANSI colors
- raw: Minimal formatting for scripts/automation

Precedence (highest to lowest):
1) CLI flag: `--output-mode`
2) A nonempty `NO_COLOR` environment variable selects no-color mode
3) Environment: `NW_OUTPUT_MODE`
4) Config: `general.output_mode`

Rich uses terminal detection for ANSI styling. Redirected output is plain by
default. `FORCE_COLOR` can request ANSI colors in redirected styled output.

Examples:

```bash
nw info device1 --output-mode raw
export NW_OUTPUT_MODE=light && nw run device1 system_info
```

Config snippet:

```yaml
general:
  output_mode: dark
```
