# Compare RouterOS state around an upgrade

Save the same device JSON before and after your upgrade, then review what
changed with `nw diff`. These commands cover interfaces, VRFs, routing-table
definitions and system resources.

## Set the device and save directory

Run from a Networka checkout with dependencies installed using `uv sync --locked`.
Use your existing inventory, SSH access and credentials. In its configuration,
set the saved file format:

```yaml
general:
  results_format: json
```

Change `TARGET` and `CONFIG` below to your inventory name and configuration path.
`TARGET` can also name a group containing only RouterOS devices. Keep the same
device names, group membership and terminal variables throughout the procedure.

```bash
TARGET="switch1"
CONFIG="./devices.yml"
mkdir -p ./captures
SAVE=$(mktemp -d ./captures/upgrade.XXXXXX)
printf 'Save directory: %s\n' "$SAVE"
```

The native JSON commands below were exercised on RouterOS 7.24.5 and 7.25.2.
Confirm support on the customer's release before the maintenance window.

## Save JSON before the upgrade

```bash
uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/interface/print detail as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/before/interfaces"

uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/ip/vrf/print detail as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/before/vrfs"

uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/routing/table/print detail as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/before/tables"

uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/system/resource/print as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/before/resources"
```

All four commands must finish successfully with exit `0` and saved results.
Resolve any failed collection before starting the upgrade. Each query has its
own directory; Networka creates a timestamped subdirectory inside it.

## Perform your upgrade and save JSON again

Use your approved upgrade procedure. Once the devices answer over SSH again,
keep the original saved output and run the identical queries:

```bash
uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/interface/print detail as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/after/interfaces"

uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/ip/vrf/print detail as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/after/vrfs"

uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/routing/table/print detail as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/after/tables"

uv run --locked nw run "$TARGET" \
  ':put [:serialize to=json options=json.no-string-conversion [/system/resource/print as-value]]' \
  --config "$CONFIG" --store-results --results-dir "$SAVE/after/resources"
```

Confirm all four commands succeeded. Run each collection once in these
directories. If you collect again, compare the exact timestamped directories
printed by Networka; a directory containing multiple collections is ambiguous.

## Compare the saved results

```bash
uv run --locked nw diff "$SAVE/before/interfaces" "$SAVE/after/interfaces" \
  --structured --key name

uv run --locked nw diff "$SAVE/before/vrfs" "$SAVE/after/vrfs" \
  --structured --key name

uv run --locked nw diff "$SAVE/before/tables" "$SAVE/after/tables" \
  --structured --key name

uv run --locked nw diff "$SAVE/before/resources" "$SAVE/after/resources" \
  --structured
```

`--key name` matches table rows by name. Resources are an object, so their
comparison has no key. All device fields remain included. A color terminal
shows DeepDiff's compact colored view; see [saved structured results](results.md#compare-saved-structured-results).

Exit `0` means no differences, `1` means differences found, and `2` means an
error or unusable saved results. Review each comparison; exit `1` alone does
not decide whether the upgrade is acceptable.

## Review the changes

| Field or state | Expected or required review |
|---|---|
| Software version and build time | Expected to change; confirm the planned target release. |
| Uptime, last-link-up times and counters | Can reset or change across the reboot and collection interval. |
| CPU load, free memory and free storage | Can change; investigate unexpectedly constrained resources. |
| Interface running/disabled state, MTU and VRF assignment | Expect preservation unless the change was planned. Investigate an in-service interface that becomes down or disabled. |
| MAC addresses | Review changes explicitly; physical-interface MAC addresses should remain the same. |
| VRFs and routing-table definitions | Expect preservation unless planned; investigate missing or unexpectedly changed entries. |

Keep both collections with the change record. These replies cover the state
listed above; apply the customer's traffic and protocol acceptance checks
separately before accepting the upgrade.
