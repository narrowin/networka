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

## Compare saved structured results

Use saved replies to see which device values changed after a software upgrade
or configuration change. Collect the same native JSON command on the same
devices twice, then compare the saved results without accessing the devices.

Save the results of a native JSON command or sequence with the existing
`nw run --store-results` option. Set `general.results_format: json` in your
configuration. The saved Networka result contains the device and command,
plus the device's reply in `output`; structured comparison decodes that reply.
The device command must itself produce valid JSON.

For example, collect a RouterOS interface table twice:

```bash
uv run nw run switch1 \
  ':put [:serialize to=json options=json.no-string-conversion [/interface/print detail as-value]]' \
  --store-results
```

Each invocation prints its saved results directory. Compare those directories
using their actual paths:

```bash
uv run nw diff ./results/run-001 ./results/run-002 --structured --key name
```

The two directory names above are examples, with no special before/after
meaning. You can also pass two saved JSON result files or two native JSON
files. No devices are accessed during structured comparison.

DeepDiff compares the complete decoded replies. Collection timestamps and
other Networka metadata are excluded from the device payload. Saved collections
must cover the same device names and exact commands; missing replies, failed
group results, incomplete summaries, malformed JSON and duplicate saved
device/command pairs produce an error. Choose a single saved run directory,
not a parent containing several runs.

`--key name` matches rows in a top-level table by their `name` field. Each row
must have a unique string or integer key. Duplicate or missing keys are errors.
Without `--key`, array order remains significant, as needed for firewall rules.
A key applies to every reply being compared, so compare table queries
separately from replies with another shape.

Exclude specific payload paths explicitly with repeatable `--exclude-path`:

```bash
uv run nw diff ./results/run-001 ./results/run-002 --structured --key name \
  --exclude-path "root['demo-bridge']['link-downs']"
```

Paths refer to the payload after indexing by `--key`, when provided. All native
fields and types are compared by default, including counters and properties
beginning with `__`. Exclusions are printed, and saved evidence is not changed.
DeepDiff is pinned to 9.2.1; incomplete comparisons are errors.

Color terminals use DeepDiff's compact colored view: changed values appear
inside the JSON structure, additions are green, removals are red, and unchanged
nested objects are collapsed. Without color, DeepDiff's text descriptions
identify additions and removals explicitly. `--output-mode json` emits the
structured changes and a comparison summary as JSONL.

Output says **Changes found** or **No differences found**. Exit status is
1 for differences, 0 for no differences and 2 for invalid inputs or unusable
evidence. Differences do not by themselves judge whether an upgrade succeeded.
Use intent checks separately for requirements such as a link being up.
The existing text and heuristic comparison modes keep their behavior.

For the verified RouterOS example, see
[prepare a CHR upgrade lab](vendors/mikrotik/chr-upgrade-lab.md).
It includes the fresh-image VRF-loss cause, exact preparation commands and
native JSON from the completed upgrade.

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
