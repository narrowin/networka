# Compare RouterOS state around an upgrade

Define what to collect once as a Networka sequence. One `nw run` invocation
collects every command in that sequence for the selected device or group.
Run it before and after your upgrade, then compare the two saved bundles.

## Define the collection once

Use your existing Networka inventory and SSH credentials. Set
`general.results_format: json` in its configuration.

Save [upgrade-state.yml](examples/upgrade-state.yml) in a `sequences/` directory
beside your main configuration file. For example, with `./devices.yml` as the
configuration, use `./sequences/upgrade-state.yml`:

```yaml
sequences:
  upgrade_state:
    description: Native RouterOS JSON for an upgrade comparison
    device_types: [mikrotik_routeros]
    commands:
      - ':put [:serialize to=json options=json.no-string-conversion [/interface/print detail as-value]]'
      - ':put [:serialize to=json options=json.no-string-conversion [/ip/vrf/print detail as-value]]'
      - ':put [:serialize to=json options=json.no-string-conversion [/routing/table/print detail as-value]]'
      - ':put [:serialize to=json options=json.no-string-conversion [/system/resource/print as-value]]'
```

Edit this list to choose what the customer needs collected. Every command must
return native JSON; these four were exercised on RouterOS 7.24.5 and 7.25.2.
Keep the command list, device names and group membership the same across each
before/after comparison.

## Collect before the upgrade

Run from a Networka checkout with dependencies installed using `uv sync --locked`.
Set your target and configuration path, and keep this terminal open:

```bash
TARGET="switch1"
CONFIG="./devices.yml"
mkdir -p ./captures
SAVE=$(mktemp -d ./captures/upgrade.XXXXXX)
printf 'Save directory: %s\n' "$SAVE"

uv run --locked nw run "$TARGET" upgrade_state \
  --config "$CONFIG" --store-results --results-dir "$SAVE/before"
```

`TARGET` can be a device or a RouterOS-only group. This invocation saves all
four replies per device, together with a sequence summary. Confirm exit `0`
and saved results before proceeding.

## Perform your upgrade and collect again

Use your approved upgrade procedure. Once SSH access returns, run the same
sequence with a new destination:

```bash
uv run --locked nw run "$TARGET" upgrade_state \
  --config "$CONFIG" --store-results --results-dir "$SAVE/after"
```

Confirm exit `0`. Run each capture once in these directories. If you collect
again, select the exact timestamped directories printed by Networka for the
comparison; keep the original capture files.

## Compare the complete bundles

```bash
uv run --locked nw diff "$SAVE/before" "$SAVE/after" --structured
```

One comparison covers every device and command in both bundles. Missing,
failed or incomplete saved collections produce an error. All device fields
remain included. Objects are compared by their fields; array order is
preserved, so row reordering also appears as a difference.

A color terminal shows DeepDiff's compact colored view. Exit `0` means no
differences, `1` means differences found, and `2` means an error or unusable
saved results. Review the differences before accepting the upgrade.

## Review the changes

| Field or state | Expected or required review |
|---|---|
| Software version and build time | Expected to change; confirm the planned target release. |
| Uptime, last-link-up times and counters | Can reset or change across the reboot and collection interval. |
| CPU load, free memory and free storage | Can change; investigate unexpectedly constrained resources. |
| Interface running/disabled state, MTU and VRF assignment | Expect preservation unless planned. Investigate an in-service interface that becomes down or disabled. |
| MAC addresses | Review changes explicitly; physical-interface MAC addresses should remain the same. |
| VRFs and routing-table definitions | Expect preservation unless planned; investigate missing or unexpectedly changed entries. |

Keep both saved bundles with the change record. These four queries cover
interfaces, VRFs, routing-table definitions and resources; apply the customer's
traffic and protocol acceptance checks separately.
