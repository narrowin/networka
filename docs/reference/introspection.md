# Config Introspection

Networka provides config introspection to answer "where did this value come from?" - useful for debugging configuration issues when values are loaded from multiple sources.

## CLI Usage

Use the `--trace` flag with `nw info` to see the source of each configuration value:

```bash
# Show device info with source provenance
nw info sw-acc1 --trace
```

Example output:

```
Device: sw-acc1
Property     Value              Source
host         192.168.1.10       config/devices/switches.yml
device_type  cisco_iosxe        config/devices/_defaults.yml
user         admin              env: NW_USER_DEFAULT
port         22                 default
```

## Source Types

The `Source` column shows where each value originated:

| Source Format | Description |
|---------------|-------------|
| `config/path/file.yml` | Value from a YAML config file |
| `config/path/file.yml:42` | Value from config file at specific line (reserved) |
| `env: NW_VAR_NAME` | Value from environment variable |
| `group: group-name` | Value inherited from device group |
| `ssh_config: ~/.ssh/config` | Value from SSH config file |
| `default` | Pydantic model default value |

Note: Line number tracking and some source types (dotenv, cli, interactive) are reserved for future use.

## Python API

For programmatic access, use the introspection classes directly.

### Querying Field History

```python
from network_toolkit.config import load_config

config = load_config("config/")
device = config.devices["sw-acc1"]

# Get the current source for a field
source = device.get_field_source("host")
if source:
    print(f"host = {source.value}")
    print(f"  from: {source.format_source()}")
    print(f"  loader: {source.loader}")

# Get full history (all values that were set)
history = device.get_field_history("device_type")
for entry in history:
    print(f"  {entry.value} <- {entry.format_source()}")
```

### Core Classes

#### LoaderType

Enum identifying the source type:

```python
from network_toolkit.introspection import LoaderType

# Currently implemented
LoaderType.CONFIG_FILE       # YAML/CSV config file
LoaderType.ENV_VAR           # Environment variable
LoaderType.GROUP             # Device group inheritance
LoaderType.SSH_CONFIG        # SSH config file
LoaderType.PYDANTIC_DEFAULT  # Model default

# Reserved for future use
LoaderType.DOTENV            # .env file (planned)
LoaderType.CLI               # CLI argument (planned)
LoaderType.INTERACTIVE       # Interactive prompt (planned)
```

#### FieldHistory

Immutable record of a single field value assignment:

```python
from network_toolkit.introspection import FieldHistory, LoaderType

entry = FieldHistory(
    field_name="host",
    value="192.168.1.1",
    loader=LoaderType.CONFIG_FILE,
    identifier="config/devices/routers.yml",
    line_number=15,
)

# Human-readable source string
print(entry.format_source())  # "config/devices/routers.yml:15"
```

#### ConfigHistory

Container tracking history for multiple fields:

```python
from network_toolkit.introspection import ConfigHistory, LoaderType

history = ConfigHistory()

# Record field values
history.record_field("host", "10.0.0.1", LoaderType.PYDANTIC_DEFAULT)
history.record_field("host", "192.168.1.1", LoaderType.CONFIG_FILE,
                     identifier="devices.yml")

# Query
current = history.get_current("host")  # Most recent value
all_entries = history.get_history("host")  # Full history
fields = history.get_all_fields()  # All tracked field names
```

### ConfigHistoryMixin

`DeviceConfig`, `DeviceGroup`, and `GeneralConfig` all include the `ConfigHistoryMixin` which provides:

- `record_field(name, value, loader, identifier?, line_number?)` - Record a value
- `get_field_history(name)` - Get all historical values
- `get_field_source(name)` - Get the current (most recent) source

```python
device = config.devices["router1"]

# These methods come from ConfigHistoryMixin
source = device.get_field_source("transport_type")
if source:
    print(f"transport_type came from {source.format_source()}")
```
