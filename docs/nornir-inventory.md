# Nornir Inventory (SimpleInventory) and Containerlab

Networka can use an existing Nornir **SimpleInventory** as its device/group inventory input. This includes Containerlab’s generated `nornir-simple-inventory.yml` out of the box (no conversion step).

## Containerlab workflow (recommended)

1) Deploy your lab (Containerlab auto-generates a Nornir inventory in the lab directory):

- Lab directory contains `nornir-simple-inventory.yml`
- `/etc/hosts` contains `clab-<lab>-<node>` hostnames

2) Create a small Networka config directory **outside** the lab directory (Containerlab recreates the lab dir on redeploy):

```yaml
# config.yml
general:
  default_transport_type: scrapli

inventory:
  source: nornir_simple
  nornir_inventory_dir: /path/to/clab-<lab-dir>
  merge_mode: replace

  # Recommended when Containerlab inventory provides username/password
  credentials_mode: inventory

  # Containerlab platform names often differ; enable mapping
  platform_mapping: netmiko_to_networka

  # Optional: connect via clab hostnames (useful for SSH ProxyJump by name)
  connect_host: containerlab_longname
```

3) Run commands using the generated inventory:

```bash
nw list devices --config /path/to/networka-config-dir
nw list groups --config /path/to/networka-config-dir
nw run mikrotik "/system/identity/print" --config /path/to/networka-config-dir
```

## Adding groups via Containerlab labels

Containerlab can write Nornir groups into `nornir-simple-inventory.yml` using node labels that start with `nornir-group`:

```yaml
topology:
  nodes:
    sw-acc1:
      labels:
        nornir-group: lab_s3n
        nornir-group-2: access
```

After redeploy (or `containerlab deploy -c`), Containerlab will emit:

- `groups: [lab_s3n, access]` on the host entry, and Networka will compile that into Networka groups so you can target `lab_s3n` or `access` on the CLI.

## SSH ProxyJump tip (local runs via jump host)

If the lab mgmt network is only reachable through a jump host, combine `connect_host: containerlab_longname` with an SSH config entry:

```sshconfig
Host debian-clab
  HostName debian-clab.orb.local
  User md

Host clab-s3n-*
  ProxyJump debian-clab
```

With Scrapli’s default `system` transport, Networka will use your local OpenSSH configuration.

## Inventory options (summary)

- `inventory.source`: `nornir_simple`
- `inventory.nornir_inventory_dir`: directory containing `hosts.(yml|yaml)` (and optional `groups/defaults`), **or** a Containerlab lab directory, **or** a direct path to a `*.yml`/`*.yaml` hosts inventory file.
- `inventory.merge_mode`: `replace` (v1)
- `inventory.credentials_mode`: `env` (default) or `inventory` (opt-in)
- `inventory.group_membership`: `extended` (default) or `direct` (nested group inheritance only applies when `groups.(yml|yaml)` exists)
- `inventory.platform_mapping`: `none` (default) or `netmiko_to_networka`
- `inventory.connect_host`: `inventory_hostname` (default), `host_key`, or `containerlab_longname`
