# User-defined Sequences

User sequences can override a packaged sequence by name and logical
platform. See the [resolution order](../../multi-vendor-support.md#sequence-resolution-order)
for project, user, device-local, and global definitions. The examples below
use the default Linux configuration directory. On macOS, use
`~/Library/Application Support/networka` as the root.

## Create your first user sequence

1. Create the directory:

- `mkdir -p ~/.config/networka/sequences/mikrotik_routeros`

2. Add a file `~/.config/networka/sequences/mikrotik_routeros/custom.yml`:

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
- `nw info my_quick_diag --vendor mikrotik_routeros` shows the selected commands and source.

4. Run the sequence:

- `nw run <device> my_quick_diag`

## Example files in this folder

- `mikrotik_routeros/custom.yml` — example user sequence for RouterOS
- `arista_eos/custom.yml` — example user sequence for Arista EOS
