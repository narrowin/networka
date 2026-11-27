# Device state is read as the device's own JSON, not parsed from text

Networka reads device state as the JSON a device returns itself, such as RouterOS `:serialize to=json` and iproute2 `-j`.
A neutral check is written once, and each platform has its own readers and normalizers that turn its replies into the fields the check compares.
Where no neutral field exists, such as a RouterOS configuration property, the check stays specific to that platform.
The one source with no JSON form, the Linux `ping` summary line, is read as text.

## Why

The first MLAG parsers read RouterOS text with regular expressions, and an empty column of an inactive bridge port shifted the next port's values.
JSON keeps field names and types.
On 2026-11-25 the operator rejected NAPALM-style getters: "lets us operate on the operational state as we get it instead of having to transform it".
The first intent draft invented a normalized observation file format, and the operator rejected that abstraction the same day.

## Considered options

- **Regular expressions or TextFSM templates per command.** Rejected: text parsers break on column layout, line wrapping and blank cells.
- **Scrapli's TextFSM and Genie parsers.** Not used: no template covered the RouterOS bridge monitor, and native JSON made them unneeded.
- **NAPALM getters, or a common model for every property.** Rejected: properties without a counterpart elsewhere would get fields that mean different things on different platforms.
- **An observation file that callers fill with normalized facts.** Rejected as an invented abstraction.

## Consequences

Adding a platform means adding its readers and normalizers, as described in [intent verification](../intent.md#add-a-platform).
