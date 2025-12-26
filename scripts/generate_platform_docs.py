#!/usr/bin/env python3
"""Generate platform documentation from the platform registry.

This script generates markdown documentation files from the platform registry
that can be included in the main documentation via pymdownx.snippets.

Generated files:
- docs/.generated/platform_support_table.md - Main platform support table
- docs/.generated/platform_capabilities.md - Detailed capability matrix
- docs/.generated/vendor_list.md - List of supported vendors
"""

from pathlib import Path

from network_toolkit.platforms.registry import PLATFORM_REGISTRY, PlatformStatus


def get_status_indicator(status: PlatformStatus) -> str:
    """Get text-based status indicator for a platform.

    Args:
        status: Platform status enum value

    Returns:
        Status indicator string with brackets
    """
    indicators = {
        PlatformStatus.IMPLEMENTED: "[I]",
        PlatformStatus.SEQUENCES_ONLY: "[S]",
        PlatformStatus.PLANNED: "[P]",
        PlatformStatus.EXPERIMENTAL: "[E]",
    }
    return indicators.get(status, "[?]")


def generate_platform_support_table() -> str:
    """Generate the main platform support table.

    Returns:
        Markdown table showing all platforms with their support status
    """
    lines = [
        "## Supported Platforms",
        "",
        "| Platform          | Vendor   | Status | Firmware | Backup | Docs                                  |",
        "| ----------------- | -------- | ------ | -------- | ------ | ------------------------------------- |",
    ]

    for _device_type, info in sorted(
        PLATFORM_REGISTRY.items(), key=lambda x: (x[1].vendor, x[1].display_name)
    ):
        status = get_status_indicator(info.status)
        firmware = "Yes" if info.capabilities.firmware_upgrade else "No"
        backup = (
            "Yes"
            if info.capabilities.config_backup or info.capabilities.comprehensive_backup
            else "No"
        )

        if info.docs_path:
            docs = f"[Guide]({info.docs_path})"
        else:
            docs = "-"

        lines.append(
            f"| {info.display_name:<17} | {info.vendor:<8} | {status:<6} | {firmware:<8} | {backup:<6} | {docs:<37} |"
        )

    lines.extend(
        [
            "",
            "Status Legend:",
            "",
            "- [I] IMPLEMENTED - Full platform support with operations and sequences",
            "- [S] SEQUENCES_ONLY - Command sequences available, operations in development",
            "- [P] PLANNED - On roadmap, not yet implemented",
            "- [E] EXPERIMENTAL - Partial implementation, unstable",
            "",
        ]
    )

    return "\n".join(lines)


def generate_capability_matrix() -> str:
    """Generate detailed capability matrix.

    Returns:
        Markdown table showing detailed capabilities for each platform
    """
    lines = [
        "## Platform Capabilities Matrix",
        "",
        "| Platform          | Firmware Upgrade | Firmware Downgrade | BIOS Upgrade | Config Backup | Comprehensive Backup |",
        "| ----------------- | ---------------- | ------------------ | ------------ | ------------- | -------------------- |",
    ]

    for _device_type, info in sorted(
        PLATFORM_REGISTRY.items(), key=lambda x: (x[1].vendor, x[1].display_name)
    ):
        if info.status != PlatformStatus.IMPLEMENTED:
            continue

        caps = info.capabilities
        fw_up = "Yes" if caps.firmware_upgrade else "No"
        fw_down = "Yes" if caps.firmware_downgrade else "No"
        bios = "Yes" if caps.bios_upgrade else "No"
        cfg_bak = "Yes" if caps.config_backup else "No"
        comp_bak = "Yes" if caps.comprehensive_backup else "No"

        lines.append(
            f"| {info.display_name:<17} | {fw_up:<16} | {fw_down:<18} | {bios:<12} | {cfg_bak:<13} | {comp_bak:<20} |"
        )

    lines.extend(
        [
            "",
            "Note: Only fully implemented platforms are shown in this matrix.",
            "",
        ]
    )

    return "\n".join(lines)


def generate_vendor_list() -> str:
    """Generate list of supported vendors with their platforms.

    Returns:
        Markdown list of vendors and their platforms
    """
    vendors = {}
    for _device_type, info in PLATFORM_REGISTRY.items():
        if info.vendor not in vendors:
            vendors[info.vendor] = []
        vendors[info.vendor].append(info)

    lines = [
        "## Supported Vendors",
        "",
    ]

    for vendor in sorted(vendors.keys()):
        lines.append(f"### {vendor}")
        lines.append("")

        for info in sorted(vendors[vendor], key=lambda x: x.display_name):
            status = get_status_indicator(info.status)
            lines.append(f"- **{info.display_name}** {status}")
            lines.append(f"  - Device Type: `{info.device_type}`")
            lines.append(f"  - Status: {info.status.value}")
            if info.description:
                lines.append(f"  - {info.description}")
            if info.docs_path:
                lines.append(f"  - [Documentation]({info.docs_path})")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate all platform documentation files."""
    # Create output directory
    output_dir = Path("docs/.generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate platform support table
    table_content = generate_platform_support_table()
    table_file = output_dir / "platform_support_table.md"
    table_file.write_text(table_content, encoding="utf-8")
    print(f"Generated: {table_file}")

    # Generate capability matrix
    matrix_content = generate_capability_matrix()
    matrix_file = output_dir / "platform_capabilities.md"
    matrix_file.write_text(matrix_content, encoding="utf-8")
    print(f"Generated: {matrix_file}")

    # Generate vendor list
    vendor_content = generate_vendor_list()
    vendor_file = output_dir / "vendor_list.md"
    vendor_file.write_text(vendor_content, encoding="utf-8")
    print(f"Generated: {vendor_file}")

    print("\nPlatform documentation generated successfully!")
    print(f"Total platforms: {len(PLATFORM_REGISTRY)}")

    # Print summary
    status_counts = {}
    for info in PLATFORM_REGISTRY.values():
        status_counts[info.status] = status_counts.get(info.status, 0) + 1

    print("\nStatus breakdown:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[0].value):
        print(f"  {status.value}: {count}")


if __name__ == "__main__":
    main()
