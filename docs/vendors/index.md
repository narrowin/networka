# Vendor support

Networka provides a common interface across multiple network operating systems. Vendor guides document platform nuances, supported operations, and recommended workflows.

<!-- AUTO-GENERATED: Do not edit the vendor list manually -->
<!-- Generated from src/network_toolkit/platforms/registry.py -->
<!-- Run: uv run python scripts/generate_platform_docs.py -->

--8<-- "docs/.generated/vendor_list.md"

## Command-Line Status Check

Use the registry capability filters to find implementations in your build.

```bash
nw firmware vendors
nw platforms list --capability config_backup
```

Note: Each vendor page follows the same structure so it’s easy to read and easy for tools/LLMs to parse: overview, identifiers, supported operations, firmware management, backups, built-in sequences, examples, and configuration tips. When adding a new vendor, mirror this structure for consistency.
