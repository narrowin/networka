# Recipes

These examples use devices and groups from your
[configuration](../configuration.md).

## Back up configurations across a group

```bash
nw backup config access_switches
```

See [backups](../backups.md) for downloading or retaining the generated files.

## Capture device health

```bash
nw run core_switches health_check --store-results
```

Choose the file format with `general.results_format` in `config.yml`.
See [results](../results.md) for comparing a later capture with a baseline.

## Upload a firmware file

```bash
nw upload router1 firmware.npk
```

This copies the file to the device. Firmware installation is a separate
operation. See the [RouterOS guide](../vendors/mikrotik/index.md#firmware-management).

## Compare operational evidence offline

The [experimental intent example](intent/README.md) compares selected facts
using native values and a shared definition of physical link status.
