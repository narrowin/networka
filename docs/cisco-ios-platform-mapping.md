# Cisco IOS Platform Mapping

## Overview

Networka supports both `cisco_ios` and `cisco_iosxe` as `device_type` values in your configuration. However, Scrapli (the underlying connection library) only has core drivers for `cisco_iosxe`, `cisco_iosxr`, and `cisco_nxos`.

To maintain backward compatibility and user convenience, Networka automatically maps `cisco_ios` to `cisco_iosxe` when creating connections.

## Technical Details

### The Problem

Scrapli's core drivers use these platform names:

- `cisco_iosxe` - For Cisco IOS-XE (and works with classic IOS)
- `cisco_iosxr` - For Cisco IOS-XR
- `cisco_nxos` - For Cisco NX-OS

There is NO `cisco_ios` platform in Scrapli.

### The Solution

Networka implements automatic platform mapping in `src/network_toolkit/credentials.py`:

```python
def _map_to_scrapli_platform(self, device_type: str) -> str:
    """Map internal device_type to Scrapli platform name."""
    platform_mapping = {
        "cisco_ios": "cisco_iosxe",
    }
    return platform_mapping.get(device_type, device_type)
```

This mapping happens transparently when building connection parameters, so users can use either:

- `device_type: cisco_ios` (mapped to cisco_iosxe)
- `device_type: cisco_iosxe` (used directly)

Both work identically.

## Configuration Examples

### Using cisco_ios (recommended for simplicity)

```yaml
devices:
  switch1:
    host: 192.168.1.10
    device_type: cisco_ios
    description: "Legacy IOS switch"
```

### Using cisco_iosxe (explicit)

```yaml
devices:
  switch2:
    host: 192.168.1.11
    device_type: cisco_iosxe
    description: "IOS-XE switch"
```

Both configurations will connect using Scrapli's `IOSXEDriver`.

## Best Practices

1. **New configurations**: Use `cisco_iosxe` for clarity and alignment with Scrapli documentation
2. **Legacy configurations**: `cisco_ios` continues to work for backward compatibility
3. **IOS-XR devices**: Use `cisco_iosxr` (no mapping needed)
4. **NX-OS devices**: Use `cisco_nxos` (no mapping needed)

## Troubleshooting

If you see errors like:

```text
Module not found! Scrapli Community platform 'cisco_ios' not found!
```

This means the platform mapping is not working. Ensure you're using the latest version of Networka where this fix is implemented.

## Related Documentation

- [Multi-vendor Support](multi-vendor-support.md)
- [Cisco IOS/IOS-XE Guide](vendors/cisco/index.md)
- [Scrapli Documentation](https://carlmontanari.github.io/scrapli/)
