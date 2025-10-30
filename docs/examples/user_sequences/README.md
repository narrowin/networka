# User-defined Sequences

Networka supports user-defined sequences layered on top of built-in sequences.

- Built-in: packaged defaults (no setup needed)
- User: `~/.config/networka/sequences/user/*.yml`
- Custom: `~/.config/networka/sequences/custom/*.yml` (highest priority)

## Create your first user sequence

1. Create the directory:

- `mkdir -p ~/.config/networka/sequences/user`

2. Add a file `~/.config/networka/sequences/user/mikrotik_custom.yml`:

```yaml
sequences:
  my_quick_diag:
    description: "Quick diagnostics"
    category: "troubleshooting"
    timeout: 30
    commands:
      - "/system/resource/print"
      - "/interface/print brief"
```

3. List sequences:

- `nw list sequences --vendor mikrotik_routeros`

4. Run the sequence:

- `nw run <device> my_quick_diag`

## Example files in this folder

- `mikrotik_routeros/custom.yml` — example user sequence for RouterOS
- `arista_eos/custom.yml` — example user sequence for Arista EOS
