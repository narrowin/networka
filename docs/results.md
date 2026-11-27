# Results

Use `--store-results` to write command or sequence output to files.

```bash
nw run router1 system_info --store-results
nw run router1 "/system/identity/print" --store-results --results-dir ./captures
```

The command reports the results directory. Networka writes a timestamped
subdirectory under `general.results_dir`, or under the directory supplied
with `--results-dir`.

Set the file format in `config.yml`. The accepted formats are `txt`, `json`,
and `yaml`.

```yaml
general:
  results_dir: ./results
  results_format: txt
```

See [output modes](output-modes.md) to control what the CLI prints.

## Compare with saved output

Before the change, save the device's command output in a text file. If
you use a stored Networka result, copy the reply without the generated
headers. After the change, pass that saved output to `nw diff` to fetch and
compare the same command on the same device.

```bash
nw diff router1 "/system/identity/print" --saved-output ./saved/router1-identity.txt
```

For a sequence, supply a directory with one saved output file per command.
Name each file `cmd_<normalized-command>.txt`. Replace spaces and path
separators with underscores and trim the leading and trailing underscores.
For example, `/system/identity/print` uses `cmd_system_identity_print.txt`.
Use `--save-current` to keep the newly fetched output.

If you already have both text outputs, compare them without a device.

```bash
nw diff before.txt after.txt
```

A comparison reports output changes. Decide which changes are expected for
the work you are doing. [Diff options](reference/cli.md#nw-diff)
