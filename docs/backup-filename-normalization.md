# Backup Filename Normalization

## Overview

The backup system now uses centralized filename normalization to ensure clean, readable filenames across all vendors.

## Changes

### New Module: `common/filename_utils.py`

Provides two main functions:

1. **`normalize_filename(text, max_length=100)`**
   - Removes command parameters (file=, name=, etc.)
   - Stops at RouterOS 'where' clauses
   - Replaces special characters with underscores
   - Collapses multiple separators
   - Limits length to reasonable size

2. **`normalize_command_output_filename(command)`**
   - Wraps normalize_filename and adds .txt extension
   - Used for command output files

### Examples

**Before:**

```text
_export_compact_file=nw-export.txt
_system_backup_save_name=nw-backup.txt
```

**After:**

```text
export_compact.txt
system_backup_save.txt
```

## Implementation

### MikroTik RouterOS

Updated `operations.py`:

- `create_backup()` - Uses `normalize_command_output_filename()` for command outputs
- `config_backup()` - Uses `normalize_command_output_filename()` for command outputs

### Cisco IOS

Updated `operations.py`:

- `config_backup()` - Uses `normalize_command_output_filename()` for command outputs

### Results Manager

Updated `results_enhanced.py`:

- `_sanitize_filename()` - Now delegates to `normalize_filename()` for consistency

## Benefits

1. **Cleaner filenames** - No ugly parameter assignments in filenames
2. **Consistency** - All vendors use same normalization logic
3. **Maintainability** - Single source of truth for filename generation
4. **Testability** - Comprehensive test coverage in `test_filename_utils.py`

## Testing

Run tests:

```bash
uv run pytest tests/test_filename_utils.py -v
uv run pytest tests/test_backup_integration.py -v
```

## Migration

No migration needed - this is a breaking change but the project has no users yet.
