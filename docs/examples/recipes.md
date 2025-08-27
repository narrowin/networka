# Recipes

Short, copy-pasteable workflows for common tasks.

## Backup configs across a group

```bash
nw backup access_switches --store-results
```

Expected output (trimmed):

```
access_switches: device sw-acc1 ... ok
access_switches: device sw-acc2 ... ok
Backups completed; results stored in results/<timestamp>
```

## Audit health across devices

```bash
nw run core_switches health_check --store-results --results-format json
```

Expected output (trimmed):

```
core_switches: step 1/3 ... ok
core_switches: step 2/3 ... ok
core_switches: step 3/3 ... ok
Sequence completed successfully; results stored
```

## Upload a firmware file to a device

```bash
nw upload rtr-01 firmware.npk
```

Expected output (trimmed):

```
Uploading firmware.npk to rtr-01 ... done
```
