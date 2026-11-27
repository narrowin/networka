# Prepare a CHR lab for an upgrade comparison

Prepare a disposable RouterOS CHR switch, save its native JSON with `nw run`,
upgrade it, and compare the saved output with `nw diff`.

The fresh 7.24.5 ARM64 image used here lacks its v7 conversion flag. Its first
package installation can erase configured VRFs and routing tables. Complete the
preparation cycle below before applying customer configuration. This procedure
is for the disposable lab; existing production hardware was not examined.

To see the verified result without deploying anything, run this from a Networka
checkout:

```bash
uv run --locked nw diff \
  docs/vendors/mikrotik/chr-upgrade-evidence/prepared-vrfs-7.24.5.json \
  docs/vendors/mikrotik/chr-upgrade-evidence/prepared-vrfs-7.25.2.json \
  --structured --key name
```

The VRF comparison returns exit `0` and prints `No differences found.` The
[recorded evidence](#read-the-recorded-evidence) also includes the interface,
resource and routing-table replies.

## Check prerequisites

Run the commands on the Linux lab machine, from the Networka checkout. Use:

- Docker, `curl`, `jq`, `sha256sum` and the project's pinned `uv` version.
- Python 3.15 or later and `uv sync --locked` for Networka.
- containerlab with native `mikrotik_chr` support. The investigation used
  [commit `06ac3ca4d`](https://github.com/srl-labs/containerlab/commit/06ac3ca4d442ce4f937b50bd7c04d5f32fb3173b)
  from [containerlab pull request 3636](https://github.com/srl-labs/containerlab/pull/3636).
  Put the qualified binary on `PATH` as `containerlab`.
- An unused `172.30.134.0/24` subnet and no existing lab named `nw-chr-upgrade`.
  Inspect deployed labs and active `nw test` processes first; leave other labs
  untouched.

On the investigation's Mac, the Linux lab machine was reached with
`orb -m mlag-external`. The remaining commands belong in that Linux shell.

## Deploy the disposable switch

Keep this first terminal open; its variables are used through cleanup.
The credentials below are the disposable CHR defaults.

```bash
CLAB=$(command -v containerlab)
LAB_ROOT=$(mktemp -d /tmp/nw-chr-upgrade.XXXXXX)
LAB_NODE=clab-nw-chr-upgrade-switch1
LAB_API=http://172.30.134.2/rest
export NW_USER_DEFAULT=admin
export NW_PASSWORD_DEFAULT=admin

cat > "$LAB_ROOT/bootstrap.rsc" <<'RSC'
/system identity set name=nw-chr-upgrade-switch1
/interface bridge add name=demo-bridge protocol-mode=none
RSC

cat > "$LAB_ROOT/topology.clab.yml" <<'YAML'
name: nw-chr-upgrade
mgmt:
  network: nw-chr-upgrade-mgmt
  ipv4-subnet: 172.30.134.0/24
topology:
  nodes:
    switch1:
      kind: mikrotik_chr
      image: mikrotik/chr:7.24.5@sha256:6313493d463267fc12e2f59cba9c0e5e32e1174fb6ebff5730f7f73aabc5ecf5
      mgmt-ipv4: 172.30.134.2
      startup-config: bootstrap.rsc
YAML

cat > "$LAB_ROOT/devices.yml" <<'YAML'
general:
  results_format: json
  ssh_known_hosts_file: /dev/null
  ssh_strict_host_key_checking: false
devices:
  switch1:
    host: 172.30.134.2
    device_type: mikrotik_routeros
YAML

sudo "$CLAB" deploy -t "$LAB_ROOT/topology.clab.yml"
```

Wait for the initial bootstrap to finish. Check its identity and release:

```bash
sudo docker logs "$LAB_NODE"
uv run --locked nw run switch1 /system/identity/print \
  --config "$LAB_ROOT/devices.yml"
uv run --locked nw run switch1 /system/resource/print \
  --config "$LAB_ROOT/devices.yml"
```

Expect `nw-chr-upgrade-switch1` and `7.24.5 (stable)`. The launcher creates the
initial `mgmt` VRF. Do not load the customer configuration yet.

## Download and serve the packages

Download the official ARM64 packages and verify their local SHA-256 values:

```bash
mkdir "$LAB_ROOT/packages"
for version in 7.24.5 7.24.7 7.25.2; do
  curl --fail --show-error --location \
    "https://download.mikrotik.com/routeros/$version/routeros-$version-arm64.npk" \
    --output "$LAB_ROOT/packages/routeros-$version-arm64.npk"
done

cat > "$LAB_ROOT/packages/SHA256SUMS" <<'SUMS'
859b4f3a223a7982edfe07c31cc455b127f298cbba1da18de372a43d1b448a11  routeros-7.24.5-arm64.npk
e798c9e01759c95c6b2c4f0b03af93e38edbf4b498555886ecde0482d14cf8bd  routeros-7.24.7-arm64.npk
376117314e47159c615397a2087b5eaf596947bc144aeaa98cacbb49494a54dc  routeros-7.25.2-arm64.npk
SUMS
(cd "$LAB_ROOT/packages" && sha256sum --check SHA256SUMS)

uv run --no-project python -m http.server 18082 \
  --bind 172.30.134.1 --directory "$LAB_ROOT/packages" \
  > "$LAB_ROOT/package-http.log" 2>&1 &
PACKAGE_HTTP_PID=$!

lab_rest() {
  curl --fail --silent --show-error --connect-timeout 5 --max-time 60 \
    --user "$NW_USER_DEFAULT:$NW_PASSWORD_DEFAULT" \
    --header 'Content-Type: application/json' "$@"
}
```

This HTTP server is bound to the disposable lab network. The package download
from MikroTik uses HTTPS. The procedure uses RouterOS HTTP fetch because the
initial investigation encountered a separate SFTP verification stall.

## Initialize the conversion flag

### Install 7.24.7 once

In the first terminal, fetch the package through the initial `mgmt` VRF.
Check the package's version, architecture and exact byte count before rebooting:

```bash
lab_rest --data '{"url":"http://172.30.134.1:18082/routeros-7.24.7-arm64.npk","address":"@mgmt","dst-path":"routeros-7.24.7-arm64.npk"}' \
  "$LAB_API/tool/fetch" &&
lab_rest "$LAB_API/file?name=routeros-7.24.7-arm64.npk" |
  jq -e 'any(.[]; .["package-version"] == "7.24.7" and
    .["package-architecture"] == "arm64" and (.size | tonumber) == 13926741)' &&
lab_rest --data '{}' "$LAB_API/system/reboot"
```

Fetch must finish successfully and the metadata check must print `true`.
The reboot call can return `[]` or close its HTTP connection while RouterOS
reboots. Confirm the installed release through the serial console before
continuing; a closed connection alone does not establish installation.

Open a second terminal on the same Linux lab machine and keep this console
open through preparation:

```bash
sudo docker exec -it clab-nw-chr-upgrade-switch1 nc 127.0.0.1 5000
```

Press Enter to show the prompt. Sign in with the disposable `admin` account
and password `admin`. After the console shows `MikroTik 7.24.7`, the first
conversion has completed. On the affected fresh image, `mgmt` is now absent
and its old service bindings are invalid.

At the RouterOS console, restore temporary SSH and HTTP access in `main`:

```routeros
/ip/vrf/print detail
/ip/service/set ssh,www vrf=main
```

These are preparation commands on the disposable switch. The desired lab
configuration is applied after returning to 7.24.5.

### Return to the starting release

Back in the first terminal, fetch 7.24.5 through `main` and request the normal
RouterOS package downgrade:

```bash
lab_rest --data '{"url":"http://172.30.134.1:18082/routeros-7.24.5-arm64.npk","address":"@main","dst-path":"routeros-7.24.5-arm64.npk"}' \
  "$LAB_API/tool/fetch" &&
lab_rest "$LAB_API/file?name=routeros-7.24.5-arm64.npk" |
  jq -e 'any(.[]; .["package-version"] == "7.24.5" and
    .["package-architecture"] == "arm64" and (.size | tonumber) == 13922637)' &&
lab_rest --data '{}' "$LAB_API/system/package/downgrade"
```

Watch the existing serial console for `MikroTik 7.24.5 (stable)`, then sign in
again. The conversion flag remains initialized after this downgrade.

### Apply the lab configuration

At the RouterOS console on 7.24.5, recreate the management VRF and its service
bindings:

```routeros
/ip/vrf/add name=mgmt interfaces=ether1 place-before=0 comment=clab-mgmt
:delay 1s
/ip/service/set ssh,www,www-ssl,api,api-ssl,winbox,telnet vrf=mgmt
/snmp/set vrf=mgmt
```

The bootstrap bridge still exists. Apply any additional configuration needed
for the upgrade exercise now. Keep this work outside `nw test`.

In the first terminal, confirm the starting state:

```bash
lab_rest "$LAB_API/system/resource" |
  jq -e '.version == "7.24.5 (stable)"'
lab_rest "$LAB_API/ip/vrf" |
  jq -e 'any(.[]; .name == "mgmt" and .interfaces == "ether1")'
lab_rest "$LAB_API/ip/service" |
  jq -e 'any(.[]; .name == "ssh" and .dynamic == "false" and
    .vrf == "mgmt" and .invalid == "false")'
```

All three checks must print `true`. The verified preparation cycle is
`7.24.5 → 7.24.7 → 7.24.5`. Creating a static routing table or merely rebooting
the fresh image did not initialize the flag.

## Save the starting JSON

Use separate directories for each query shape. Resource output is an object;
the other queries are tables.

```bash
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/ip/vrf/print detail as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-001/vrfs"
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/routing/table/print detail as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-001/tables"
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/interface/print detail as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-001/interfaces"
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/system/resource/print as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-001/resources"
```

The resource command deliberately omits `detail`; RouterOS rejects that
parameter on `/system/resource/print`.

## Perform the actual upgrade

Fetch and install the target package through the restored `mgmt` VRF:

```bash
lab_rest --data '{"url":"http://172.30.134.1:18082/routeros-7.25.2-arm64.npk","address":"@mgmt","dst-path":"routeros-7.25.2-arm64.npk"}' \
  "$LAB_API/tool/fetch" &&
lab_rest "$LAB_API/file?name=routeros-7.25.2-arm64.npk" |
  jq -e 'any(.[]; .["package-version"] == "7.25.2" and
    .["package-architecture"] == "arm64" and (.size | tonumber) == 13988453)' &&
lab_rest --data '{}' "$LAB_API/system/reboot"
```

Wait for the serial console to show `MikroTik 7.25.2` and for SSH/HTTP to
answer. Check the target release and preserved management bindings:

```bash
lab_rest "$LAB_API/system/resource" | jq -e '.version == "7.25.2"'
lab_rest "$LAB_API/ip/vrf" |
  jq -e 'any(.[]; .name == "mgmt" and .interfaces == "ether1")'
lab_rest "$LAB_API/ip/service" |
  jq -e 'any(.[]; .name == "ssh" and .dynamic == "false" and
    .vrf == "mgmt" and .invalid == "false")'
```

The verified prepared-base upgrade needed no management repair here.

## Save and compare the target JSON

Collect exactly the same queries again:

```bash
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/ip/vrf/print detail as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-002/vrfs"
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/routing/table/print detail as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-002/tables"
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/interface/print detail as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-002/interfaces"
uv run --locked nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/system/resource/print as-value]]' \
  --config "$LAB_ROOT/devices.yml" --store-results \
  --results-dir "$LAB_ROOT/collection-002/resources"

uv run --locked nw diff "$LAB_ROOT/collection-001/vrfs" \
  "$LAB_ROOT/collection-002/vrfs" --structured --key name
uv run --locked nw diff "$LAB_ROOT/collection-001/tables" \
  "$LAB_ROOT/collection-002/tables" --structured --key name
uv run --locked nw diff "$LAB_ROOT/collection-001/interfaces" \
  "$LAB_ROOT/collection-002/interfaces" --structured --key name
uv run --locked nw diff "$LAB_ROOT/collection-001/resources" \
  "$LAB_ROOT/collection-002/resources" --structured
```

The recorded VRF and routing-table comparisons returned exit `0`:

```text
  unchanged
No differences found.
```

Interface and resource comparisons returned exit `1`. The interface differences
were last-link-up times and the virtual `mgmt` interface MAC address; that MAC
also changed in the ordinary-reboot control. Physical-interface MAC, MTU,
running/disabled values and VRF assignment were preserved. Resources showed
the new release/build time and volatile CPU, memory, disk, uptime and write
values. No fields were excluded.

Differences alone do not judge upgrade acceptance. See
[saved structured results](../../results.md#compare-saved-structured-results)
for comparison semantics and exit codes.

## Clean up

In the first terminal, destroy only this lab and stop its package server:

```bash
sudo "$CLAB" destroy -t "$LAB_ROOT/topology.clab.yml" --cleanup
kill "$PACKAGE_HTTP_PID"
```

The saved collections remain under `$LAB_ROOT`. The serial client disconnects
when its node is removed.

## Understand the root cause

Read-only inspection of the guest disk showed v7 VRF configuration without
logical store `/nova/store/r5/version`. RouterOS's `/nova/bin/crossfig` reads
row `1`, unsigned-integer field `1` from that store. A nonzero value skips its
legacy v6 conversion block. With the value absent/zero, it clears the v7
destination stores, including `net/vrf` and `r5/routing/routing-table`, before
importing legacy v6 state. It then writes field `1 = 1` into row `1`.

The fresh image already had v7 state, so there were no matching legacy VRFs
to restore after that clearing. Services retained references to the erased
VRF, causing the observed invalid `vrf=*1` bindings.

The observed flag lifecycle was:

| State | Stored conversion flag | Result |
|---|---|---|
| Fresh 7.24.5 | Absent | mgmt exists |
| Explicit static table plus ordinary reboot | Still absent | mgmt and static table exist |
| First 7.24.5 → 7.24.7 package installation | 1 | mgmt and static table erased |
| Return to 7.24.5 | 1 | Initialized base available |
| Restore lab configuration, then 7.24.5 → 7.25.2 | 1 | mgmt and routing tables preserved |

The serialized conversion row after initialization was `4d320100000901`.
The explicit force-conversion file `/rw/FORCE_CROSSFIG` was absent throughout.
All inspection was read-only; no private configuration flag was edited.

The initial explanation blaming the 7.25.2 transition was incomplete. The
fresh-image first-conversion condition also reproduced on the 7.24 branch.
CLI-created, REST-created, empty and bridge-bound VRFs all disappeared in
the unprepared control. Ordinary reboot and QMP reset controls preserved
the VRF. The decisive comparisons kept the containerlab launcher/reboot
watchers stopped, excluding their activity as the cause.

## Read the recorded evidence

The investigation was performed on 27 November 2026 with the pinned ARM64
image above, QEMU TCG, one vCPU and 256 MiB RAM. Networka was commit
`01343875ab803972dcb9a654f68647618624bdc3`. The same guest disk was upgraded
in place; the node was not replaced with an image of the target release.

These files contain the complete native JSON payloads extracted from the
saved `nw run` envelopes. Fields and types are retained; Networka metadata
and local paths are not included:

| Reply | 7.24.5 | 7.25.2 |
|---|---|---|
| VRFs | [Starting JSON](chr-upgrade-evidence/prepared-vrfs-7.24.5.json) | [Target JSON](chr-upgrade-evidence/prepared-vrfs-7.25.2.json) |
| Routing tables | [Starting JSON](chr-upgrade-evidence/prepared-tables-7.24.5.json) | [Target JSON](chr-upgrade-evidence/prepared-tables-7.25.2.json) |
| Interfaces | [Starting JSON](chr-upgrade-evidence/prepared-interfaces-7.24.5.json) | [Target JSON](chr-upgrade-evidence/prepared-interfaces-7.25.2.json) |
| Resources | [Starting JSON](chr-upgrade-evidence/prepared-resources-7.24.5.json) | [Target JSON](chr-upgrade-evidence/prepared-resources-7.25.2.json) |

[The evidence summary](chr-upgrade-evidence/investigation.json) records the
flag values, converter locations and comparison exit codes. Firmware binaries,
full disk copies, generated SSH keys and credentials are excluded.

The package transfer checked local SHA-256 values and the device's exact
package metadata/size. A full remote-file SHA-256 read-back was not completed.
No physical-switch or forwarding acceptance is claimed.

## Troubleshoot the preparation

- **SSH/HTTP stop answering after the first installation:** inspect the
  serial console. On this affected fresh image, use the documented temporary
  `ssh,www vrf=main` binding before the downgrade. Keep the original output
  if investigating a different failure.
- **The first metadata check fails or fetch does not finish:** stop before
  rebooting. Check the package HTTP log, version, architecture, byte count,
  management subnet and fetch VRF. Use `@mgmt` before initialization and
  `@main` after the first conversion erased that VRF.
- **A diff returns exit 2:** confirm both collections cover identical device
  names and exact commands, use `results_format: json`, and compare the
  resource object separately from tables indexed with `--key name`.

The upstream fresh-image conversion issue remains outside Networka's code.
This guide documents the verified disposable-lab preparation; it does not
install a RouterOS patch or introduce automatic preparation into `nw test`.
The separate SFTP verification stall requires its own diagnosis or fix.
