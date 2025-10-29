# Transport Selection

Networka supports pluggable connection transports. Today, Scrapli is the default and stable choice. A Netmiko-based transport via Nornir is planned.

## Current status

- Default transport: `scrapli` (stable)
- Config default override: `general.default_transport_type` in `config/config.yml`
- Per-device override: `transport_type` in a device entry
- CLI override: `--transport` on commands like `nw run`, `nw cli`, `nw info`
- nornir-netmiko: not yet supported but coming soon

## How precedence works

1. CLI `--transport` if provided
2. Device `transport_type` if set
3. Global `general.default_transport_type` (defaults to `scrapli`)

## Examples

```bash
# Use default transport (scrapli)
nw run sw-acc1 "/system/identity/print"

# Force transport per run
nw run sw-acc1 "/system/identity/print" --transport scrapli

# Set default transport in config/config.yml
general:
  default_transport_type: scrapli
```

## Notes

- Transport selection affects how connections and commands are executed.
- Some features may be transport-specific. The Scrapli transport is the reference implementation.
- nornir-netmiko is under active development and will be documented here when available.
- Windows: Scrapli is not officially supported on native Windows. Prefer WSL2/Cygwin for a POSIX environment; native use is best-effort.
