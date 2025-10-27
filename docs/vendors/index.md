# Vendor support

Networka provides a common interface across multiple network operating systems. Vendor guides document platform nuances, supported operations, and recommended workflows.

- MikroTik RouterOS — see guide
- Cisco IOS / IOS-XE — see guide
- Arista EOS — needs testing
- Juniper JunOS — needs testing
- Nokia SR Linux — see guide

Note: To see which vendors currently support firmware and backup operations in your build, run:

```bash
nw firmware vendors
nw backup vendors
```

Note: Each vendor page follows the same structure so it’s easy to read and easy for tools/LLMs to parse: overview, identifiers, supported operations, firmware management, backups, built-in sequences, examples, and configuration tips. When adding a new vendor, mirror this structure for consistency.
