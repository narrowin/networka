# Recipes

These examples use devices and groups from your
[configuration](../configuration.md).

## Back up configurations across a group

```bash
nw backup config access_switches
```

See [backups](../backups.md) for downloading or retaining the generated files.

## Capture device state

```bash
nw run core_switches health_check --store-results
```

Choose the file format with `general.results_format` in `config.yml`.
See [results](../results.md) for comparing a later capture with saved output.

## Upload a firmware file

```bash
nw upload router1 firmware.npk
```

This copies the file to the device. Firmware installation is a separate
operation. See the [RouterOS guide](../vendors/mikrotik/index.md#firmware-management).

## Check device state against saved replies

The [intent verification guide](../intent.md) shows how to declare expected
state and compare it with saved device replies.
