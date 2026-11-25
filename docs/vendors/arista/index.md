# Arista EOS

Supported identifiers: `arista_eos`

## Highlights

The packaged Scrapli catalog includes `arista_eos`. Inspect the active
definition and available sequences with `nw platforms info arista_eos`.
The operations registry has no vendor-specific firmware or backup implementation.

## Quickstart

### Run

```bash
nw run --platform arista_eos 198.51.100.30 "show version" --interactive-auth
```

### Validate (expected output, trimmed)

```
Interactive authentication mode enabled
Username: admin
Password: ********
Executing on 198.51.100.30: show version
Arista ...
Command completed successfully
```

## Examples

```bash
nw run eos1 "show version"
```
See [user sequence examples](../../examples/user_sequences/README.md) for local overrides.
