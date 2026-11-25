# Adding platform support

## Overview

Networka uses a logical `device_type` to select both connection behavior and
sequences. Check three layers when adding support.

| Layer | Source |
| --- | --- |
| Connection definition | Packaged Scrapli YAML or the active `SCRAPLI_DEFINITIONS_PATH` directory |
| Sequences | Networka's packaged files and the operator's sequence configuration |
| Vendor operations | Networka's platform registry and operation handlers |

Device qualification records the platform, OS version, and operations that
were exercised.

## Quick start

Inspect the platform before adding code.

```bash
nw platforms list
nw platforms info mikrotik_routeros
```

An installed definition lets Networka select that name for a command
session. Choose the logical type in inventory or pass it with `--platform`
for a raw IP. A connection alias can select the same Scrapli definition as
another platform while retaining its own sequence and operation names.
See [transport selection](transport.md).

## Step-by-step implementation guide

### Add a sequence

Start with one read-only task in an operator configuration. For a project,
put the sequence under `sequences/<device_type>/common.yml` next to
`config.yml`.

```yaml
sequences:
  system_info:
    description: System information
    commands:
      - show version
```

Inspect the selected source and commands.

```bash
nw info system_info --vendor cisco_iosxe --config ./config
```

Use `src/network_toolkit/builtin_sequences/<device_type>/common.yml` for a
maintained sequence shipped with Networka. Follow the
[sequence resolution order](multi-vendor-support.md#sequence-resolution-order)
for project or user overrides.

### Register vendor operations

Add a registry entry when reporting maintained sequences or implementing
vendor-specific operations. Work from the existing `PlatformInfo` entries
in `src/network_toolkit/platforms/registry.py`. For an operation, implement
the relevant `PlatformOperations` methods using one of the existing
platform implementations as the reference. Wire the handler into
`get_platform_operations` in `src/network_toolkit/platforms/factory.py`.
The registry records capability metadata. The factory creates the handler.

Set the individual capability flags to match implemented behavior. Preserve
`platform` as the hardware architecture field when a firmware operation uses
it. Use `nw platforms info` to verify the registry flags and definition
selection independently.

Regenerate the registry reference after changing it.

```bash
uv run --locked python scripts/generate_platform_docs.py
```

## Platform status progression

Use the status in the registry to describe Networka's implementation scope.
`sequences_only` indicates maintained sequences with no vendor operation
handlers. `implemented` indicates registered operations. The capability flags
identify which operations. A definition can be available for a platform whose
registry status is planned.

## Troubleshooting

- If a definition is missing, inspect the active catalog. An override directory
  supplies all the named definitions for that invocation.
- If a sequence name selects different commands than expected, inspect the
  logical platform or the configured device with `nw info`.
- If a vendor operation is unavailable, check the corresponding capability in
  `nw platforms info`.

## Checklist

- Confirm that installed definition lookup and alias selection work offline.
- Inspect the packaged sequence and its winning source.
- Record the approved device target, software version, commands, and results
  when qualifying device behavior.
- Run the [development checks](development.md) and update the applicable
  [vendor guide](vendors/index.md).

## Resources

- [Platform compatibility](platform-compatibility.md)
- [Multi-vendor support](multi-vendor-support.md)
- [Scrapli platform definitions](https://carlmontanari.github.io/scrapli/details/#platform-definitions)
