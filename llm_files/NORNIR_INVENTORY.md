# Nornir SimpleInventory as an Input Source (Plan)

This document describes a step-by-step plan to let Networka use an existing Nornir **SimpleInventory** (hosts/groups/defaults YAML) as an *input inventory source*, while **keeping Networka’s execution logic unchanged**.

The core idea is:

1. Let Nornir perform its inventory normalization (defaults + group inheritance).
2. Compile the normalized Nornir `Inventory` into Networka’s existing internal structures:
   - `NetworkConfig.devices: dict[str, DeviceConfig]`
   - `NetworkConfig.device_groups: dict[str, DeviceGroup]` (membership-only groups)
3. Continue using all existing Networka code paths (`get_group_members`, credential resolution, execution, sequences, results, etc.).

This is intentionally *not* “switching Networka to Nornir internally”; it is an adapter that makes Networka interoperable with Nornir inventories.

---

## Goals

- Accept an existing Nornir SimpleInventory directory as a drop-in inventory source.
- Keep Networka execution and feature behavior stable (commands, sequences, results, retries).
- Minimize refactoring by compiling into `NetworkConfig.devices`/`device_groups`.
- Provide clear precedence rules for credentials and connection parameters.
- Keep the feature optional (only required when the user opts into Nornir inventory).

## Assumptions (explicit)

- Targeting the **Nornir SimpleInventory file format** (hosts/groups/defaults YAML) and Containerlab’s generated single-file inventory.
- Inventory normalization follows Nornir’s documented inheritance model (defaults → groups → hosts) implemented inside Networka (no runtime dependency on the `nornir` Python package for v1).
- Networka still requires its own modular `config/config.yml` to configure `general/`, sequences, file operations, etc.; only hosts/groups are sourced from Nornir.
- Containerlab compatibility is a first-class goal: Containerlab generates a single-file “Simple Inventory” (`nornir-simple-inventory.yml`) which is equivalent to a `hosts.yaml` file with per-host `groups`.

## Non-goals (initial scope)

- Full migration of Networka’s internal model to Nornir objects.
- Supporting dynamic inventory plugins (NetBox, etc.) beyond SimpleInventory.
- Preserving Networka tag-driven grouping semantics (`match_tags`). (User accepted losing tags for now.)
- Implementing Nornir task execution (`nr.run`) or Nornir connection plugins.
- Depending on the `nornir` Python package at runtime (v1 is dependency-free).

---

## Why this is the best approach (for now)

- **Lowest blast radius:** all call sites expect `config.devices` and `config.get_group_members()`; compiling into these avoids rewriting large parts of CLI/API/credentials.
- **Uses Nornir where it’s strongest:** inventory normalization and inheritance rules (defaults → groups → hosts).
- **Keeps Networka’s value:** sequences, multi-vendor command resolution, result storage, interactive auth, file operations, and existing transports remain untouched.
- **Incremental path:** if Networka ever wants to “go full Nornir” later, this adapter becomes a stepping stone and can be kept for compatibility.

### Why v1 does not use the `nornir` Python library

Even though Nornir already provides inventory loaders and normalization, v1 intentionally implements a small subset of SimpleInventory parsing/merging directly:

- **Keep dependencies and operations simple:** Networka already depends on `pyyaml`. Adding `nornir` as a runtime dependency introduces packaging/compatibility concerns and plugin configuration complexity.
- **Glue logic is still required either way:** Networka’s CLI/API/execution expects `NetworkConfig.devices` and `NetworkConfig.device_groups`, plus Networka-specific policies (`credentials_mode`, `connect_host`, platform mapping, ambiguity errors). Using Nornir would not remove the adapter; it would only change how the raw inventory is normalized.
- **Containerlab output support:** Containerlab generates a single-file `nornir-simple-inventory.yml` (hosts-only with per-host `groups:`). Supporting this requires layout detection and special-case handling regardless of whether Nornir is used.

This is a deliberate tradeoff: implement a narrow, well-tested subset (hostname/platform/groups/creds) and keep behavior predictable.

---

## Possible next step (future enhancement): optional `nornir`-backed loader

If strict compliance with Nornir’s evolving merge semantics becomes important, a future enhancement can make Nornir usage optional:

### Design

- If `nornir` is installed, load inventory via Nornir’s SimpleInventory plugin and use `Host.get_connection_parameters()` as the authoritative normalized values.
- If not installed, fall back to the current dependency-free YAML parser/normalizer.
- Keep all Networka-specific compilation steps (to `NetworkConfig.devices/device_groups`) unchanged.

### Benefits

- Tracks Nornir behavior changes “for free” when users opt into the dependency.
- Maintains a lightweight default path for users who just want containerlab/simple YAML support.

### Remaining glue logic (still required)

Even with Nornir present, Networka must still:

- Compile Nornir inventory objects into Networka models (`devices`, `device_groups`).
- Apply `connect_host` policy (e.g., containerlab longnames for ProxyJump workflows).
- Apply platform mapping (e.g., `mikrotik_ros` → `mikrotik_routeros`).
- Enforce Networka’s env-credential ambiguity policy under `credentials_mode: env`.

### Suggested guardrail test (to detect drift)

- Add a small test suite (skipped when `nornir` is not installed) that loads fixture inventories both ways and asserts that effective fields (`hostname`, `platform`, `port`, `username`, `password`, group inheritance) match Nornir’s results. This provides early warning if Nornir semantics change.

---

## User experience (target state)

### Configuration

Networka config remains the modular structure for everything except hosts/groups:

```text
config/
├── config.yml
├── sequences/
└── (optional) devices/ groups/   # ignored or merged depending on settings
```

Nornir inventory lives in its standard files (usually outside or inside `config/`):

```text
nornir_inventory/
├── hosts.yaml
├── groups.yaml
└── defaults.yaml
```

Containerlab generates a single-file Nornir inventory in the lab directory:

```text
<lab-dir>/
└── nornir-simple-inventory.yml
```

`config/config.yml` opts into Nornir inventory:

```yaml
inventory:
  source: nornir_simple
  nornir_inventory_dir: ./nornir_inventory
  credentials_mode: env            # env | inventory
  group_membership: extended       # extended | direct (default: extended)
  platform_mapping: none           # none | netmiko_to_networka
  merge_mode: replace              # v1: replace only
```

### CLI behavior

- `nw list devices`, `nw run`, and completions work the same because they still see `config.devices`.
- Groups are available by name and resolve via `get_group_members` exactly as before.
- Tag-based groups are not created (unless added later).

---

## Inventory semantics: mapping spec

## Naming constraints (critical)

Networka currently uses device/group names in:

- CLI target expressions (`nw run <target> ...`)
- environment variable lookups (`NW_USER_<NAME>`, `NW_PASSWORD_<NAME>`)

Shells do not reliably support exporting env vars with characters like spaces or `.` in names, and Networka’s current env-var normalization only replaces `-` with `_`. Because of this, host/group naming must be decided up front:

- **Strict (recommended):** require Nornir host keys and group names to match a safe pattern (e.g., `^[A-Za-z0-9_-]+$`), otherwise error with a clear message.

This keeps behavior straightforward and avoids introducing “hidden” renaming that would change CLI targets, env-var lookups, and result paths.

### Host → DeviceConfig

For each normalized Nornir host `h` in `nr.inventory.hosts`, extract effective connection fields via Nornir’s own resolution helpers (to avoid re-implementing inheritance):

- `conn = h.get_connection_parameters()` (default connection parameters)

- `device_name` = `h.name`
- `DeviceConfig.host` = `conn.hostname` (required; error if missing)
- `DeviceConfig.device_type` = `conn.platform` (treat Nornir “platform” as Networka device_type; error or default policy if missing)
- `DeviceConfig.port` = `conn.port` if provided
- Optional metadata (best-effort):
  - `description` from `h.data.get("description")`
  - `model` from `h.data.get("model")`
  - `location` from `h.data.get("location")`
  - `tags` ignored initially

### What we intentionally ignore (initially)

Nornir inventory can carry additional fields (notably `connection_options`, arbitrary `data`, and per-group/per-default attributes). To keep Networka execution stable, the initial adapter should ignore:

- `connection_options` (any plugin-specific extras)
- Nornir “variables” beyond the small metadata fields listed above
- any attempt to translate Nornir runner settings (threads, etc.) into Networka (Networka already has its own parallelism)

These can be mapped later into Networka’s `DeviceConfig.overrides`/`GeneralConfig` if needed, but doing so early risks subtle behavior changes.

### Default platform policy (decided)

If a host has no effective `platform` after Nornir normalization:

- Fail fast with a clear configuration error identifying affected hosts

Rationale: `platform` drives driver selection and sequence/vendor behavior. A missing `platform` is almost always an inventory mistake and should be corrected rather than silently degraded.

### Credentials behavior

Networka’s credential resolver currently prioritizes:
1) interactive overrides
2) `DeviceConfig.user/password`
3) device-specific `NW_*`
4) group credentials/env
5) default `NW_*`

To avoid surprising users, default behavior should be:

- `credentials_mode: env` (default):
  - Do **not** set `DeviceConfig.user/password` from Nornir inventory.
  - Networka continues to use `NW_*` and interactive auth as today.

Optional behavior:

- `credentials_mode: inventory`:
  - Set `DeviceConfig.user = conn.username` and `DeviceConfig.password = conn.password` when present after normalization.
  - This makes inventory creds take precedence (because they appear as device config values).

### Groups: membership compilation

Networka groups are lists of members (and optionally tag matching). Nornir groups are inheritance containers.

We can compile membership-only groups as follows:

- For each host `h`, collect groups:
  - `direct` mode: use `h.groups` only
  - `extended` mode (default): use `h.extended_groups()` (includes nested/inherited groups)
- For each group `g` in the chosen set:
  - Add `h.name` to `DeviceGroup.members` for `g.name`
  - Set `DeviceGroup.description` from `g.data.get("description")` or `"Imported from Nornir"`

This produces a stable `config.device_groups` dictionary compatible with `get_group_members()`.

Important Networka nuance:

- Networka’s current group credential resolution checks group-level environment variables only if `DeviceGroup.credentials` is present (even if empty). To preserve the ability to use group env vars (e.g., `NW_USER_CORE`, `NW_PASSWORD_CORE`) with imported Nornir groups, the adapter should set `DeviceGroup.credentials = GroupCredentials()` (empty) for each compiled group, unless explicitly disabled.

#### Group env credential ambiguity policy (decided for v1)

When `credentials_mode: env` is used, Networka may resolve credentials from group-level env vars. In Nornir, conflicts are resolved by explicit layering/merge order, but Networka’s current group env behavior is effectively “first match wins” and does not encode intent.

To keep the implementation small and avoid surprising users with implicit precedence rules, v1 will:

- Allow group env credentials only when there is **no ambiguity**.
- If a device belongs to multiple groups that each provide group env credentials (e.g., both `NW_PASSWORD_<GROUP>` are set), fail fast with an actionable error listing:
  - the device name
  - the groups that matched
  - the exact env vars detected
  - remediation options:
    - move creds to device env vars (`NW_USER_<DEVICE>`, `NW_PASSWORD_<DEVICE>`)
    - consolidate creds into a single group env var
    - switch to `credentials_mode: inventory` so Nornir normalization provides one effective credential set

### Platform mapping (optional)

Nornir inventories often use Netmiko-ish platform names; Networka uses its own `device_type` keys (and maps some to Scrapli).

Add an optional mapping mode:

- `platform_mapping: none` (default): trust that inventory uses Networka-compatible device types.
- `platform_mapping: netmiko_to_networka`: translate common Netmiko names to Networka device types (e.g. `cisco_xe` → `cisco_iosxe`).

This mapping should be explicit and documented to prevent silent mismatches.

---

## Implementation plan (step-by-step)

### Phase 0 — Decide configuration contract (1 small PR)

1. Add a new top-level optional config section to `config.yml`:
   - `inventory.source` with allowed values: `networka` (default), `nornir_simple`
   - `inventory.nornir_inventory_dir` path (required when `nornir_simple`)
     - Decided: relative paths resolve relative to Networka config dir (not CWD).
     - May point to either:
       - a directory containing `hosts.(yaml|yml)` (and optional `groups.(yaml|yml)`, `defaults.(yaml|yml)`), or
       - a directory containing Containerlab’s `nornir-simple-inventory.(yaml|yml)`, or
       - a direct path to a single inventory file (`*.yaml|*.yml`) containing host entries (Containerlab-style).
   - `inventory.merge_mode`: `replace` (v1 only; `merge` explicitly out of scope)
   - `inventory.credentials_mode`: `env|inventory`
   - `inventory.group_membership`: `extended|direct`
   - `inventory.platform_mapping`: `none|netmiko_to_networka`
2. Update JSON schema export (if used) and docs to reflect the new fields.

### Phase 1 — Add Nornir loader + compiler (adapter module)

Create a dedicated module, e.g.:

- `src/network_toolkit/inventory/nornir_simple.py`

Responsibilities:

1. Resolve the inventory input path relative to the Networka config directory when a relative path is provided.
2. Detect supported layouts (support both `.yaml` and `.yml`):
   - **Standard SimpleInventory directory:** `hosts.(yaml|yml)` present (optional `groups.(yaml|yml)`, `defaults.(yaml|yml)`).
   - **Containerlab directory:** `nornir-simple-inventory.(yaml|yml)` present.
   - **Single-file hosts inventory:** a direct `*.yaml|*.yml` file containing top-level host mappings (Containerlab-style).
3. Load and normalize inventory (v1):
   - Parse YAML directly (no `nornir` dependency).
   - Implement Nornir-style inheritance for the needed fields:
     - `defaults` merged into effective host config
     - `groups` support nested `groups:` and merge parents → child
     - host `groups:` merged in listed order
     - host fields override everything
   - Containerlab/single-file inventories skip groups/defaults normalization (they already emit fully populated host fields), but still compile `groups:` membership.
3. Compile to Networka models:
   - `devices: dict[str, DeviceConfig]`
   - `device_groups: dict[str, DeviceGroup]`
4. Return compiled structures plus optional notices/warnings.

Implementation notes:

- Keep the implementation dependency-free (PyYAML is already a dependency).
- If future correctness/edge-cases demand it, consider adding an optional `nornir`-based loader later, but keep v1 stable and simple.
- Enforce strict safe host/group names (see Naming constraints) and fail fast with an actionable error message listing invalid names.
- Prefer `Host.get_connection_parameters()` for effective hostname/platform/port/username/password instead of reading raw host attributes directly.

### Phase 2 — Integrate into NetworkConfig loading

Modify config loading (where modular config is assembled) to:

1. Load `general`, sequences, vendor sequences, file ops as today.
2. Based on `inventory.source`:
   - `networka`: keep current devices/groups loading.
   - `nornir_simple`:
     - Load and compile Nornir inventory
     - Apply `merge_mode`:
       - `replace` (v1): ignore/overwrite any loaded devices/groups
3. Ensure `config.devices`/`config.device_groups` are populated before anything else uses them.

### Phase 3 — Tighten behaviors and error messages

1. Missing/invalid inventory files should fail early with actionable errors (path, required filenames).
2. Add warnings/notices for:
   - missing `hostname` for a host (cannot connect; should be an error)
   - missing `platform` for a host (v1: hard error)
   - unknown platform mapping when `platform_mapping` enabled
3. Add a specific failure mode (v1) when `credentials_mode: env`:
   - detect ambiguous group-level env credentials per device and raise a clear configuration error (see Group env credential ambiguity policy)

### Phase 4 — Update documentation + examples

1. Add a “Using Nornir SimpleInventory” section to docs:
   - expected inventory file layout
   - config.yml snippet
   - how credentials work in `env` vs `inventory` mode
2. Add a minimal example inventory directory in docs (not necessarily shipped in package).

### Phase 5 — Tests (unit tests only)

Add tests that:

1. Load a fixture SimpleInventory and verify:
   - `config.devices` contains expected hostnames/platform/port
   - `config.device_groups` contains expected membership
   - nested group membership works under `extended`
2. Load a fixture Containerlab-style `nornir-simple-inventory.yml` and verify:
   - `config.devices` loads hosts from a single-file inventory
   - `groups:` lists are compiled into `config.device_groups` membership
   - missing `platform` fails fast
2. Verify credential precedence stays stable under `credentials_mode: env`.
3. Verify `credentials_mode: inventory` sets `DeviceConfig.user/password` and changes resolution accordingly.
4. Verify group env credential lookup works for compiled groups (requires `DeviceGroup.credentials` to be present, even if empty).
5. Verify ambiguous group env credentials fail fast under `credentials_mode: env` with a clear message and remediation guidance.

Dependency strategy for tests:

- Add `nornir` to dev/test extras (or skip tests when not installed).

---

## Dependencies and packaging

v1 does not require the `nornir` Python package. Networka parses the SimpleInventory YAML format directly.

---

## Risks and mitigations

- **Credential precedence surprises:** default to `credentials_mode: env`; require explicit opt-in to use inventory creds.
- **Platform naming mismatch:** document that `host.platform` must match Networka `device_type`, or enable explicit mapping.
- **Group semantics differences:** compiled groups are “membership-only”; inheritance semantics are already resolved by Nornir normalization.
- **Name/ENV friction:** enforce safe naming (see Naming constraints) to keep CLI and env-var behavior predictable.
- **Future tag reintroduction:** tags can be re-added later by pulling `tags` from `host.data` and building tag-match groups, but keep it out of initial scope.

---

## Acceptance criteria (definition of done)

- With `inventory.source: nornir_simple`, Networka:
  - loads hosts + groups + defaults from Nornir inventory
  - loads Containerlab’s `nornir-simple-inventory.(yml|yaml)` as an accepted input source
  - exposes devices and groups through existing CLI/API behavior
  - runs commands/sequences unchanged (execution stack untouched)
- Docs include a complete, copy/pasteable example.
- Tests cover at least:
  - device compilation
  - group membership compilation
  - credential mode behavior

---

## Open questions (decide before implementation)

None for v1.
