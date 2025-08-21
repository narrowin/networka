# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Config initialization command for a streamlined, powerful starter setup.

Creates a complete starter configuration with:
- .env file with credential templates
- config/config.yml with core settings
- config/devices/ with MikroTik and Cisco examples
- config/groups/ with tag-based and explicit groups
- config/sequences/ with global and vendor-specific sequences
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.logging import console, setup_logging


def create_env_file(target_dir: Path) -> None:
    """Create a minimal .env file with credential templates and options."""
    env_content = """# Network Toolkit Environment Variables
# Default credentials (used when device-specific vars not set)
NW_USER_DEFAULT=admin
NW_PASSWORD_DEFAULT=changeme123

# Device-specific credential examples (optional)
# NW_SW_OFFICE_01_USER=admin
# NW_SW_OFFICE_01_PASSWORD=device_specific_password
# NW_RTR_MAIN_01_USER=admin
# NW_RTR_MAIN_01_PASSWORD=router_password

# Results directory override (optional)
# NW_RESULTS_DIR=./results

# Test results directory override (optional)
# NW_TEST_RESULTS_DIR=./test_results
"""
    env_file = target_dir / ".env"
    env_file.write_text(env_content.strip() + "\n")
    console.print(f"[green]Created .env file: {env_file}[/green]")


def create_config_yml(config_dir: Path) -> None:
    """Create minimal config.yml with core settings and helpful comments."""
    config_content = """# Network Toolkit General Configuration
general:
  # Directory paths
  results_dir: "./results"
  # Transport type: ssh (default) or other supported transports
  transport: "ssh"
  # Connection timeouts
  timeout: 30
  # Output formatting
  output_mode: "default"  # default, light, dark, no-color, raw

# Note:
# - Devices are defined in config/devices/
# - Groups are defined in config/groups/
# - Sequences are defined in config/sequences/
# - Vendor-specific sequences are mapped via config/sequences/vendor.yml
"""
    config_file = config_dir / "config.yml"
    config_file.write_text(config_content.strip() + "\n")
    console.print(f"[green]Created config file: {config_file}[/green]")


def create_example_devices(devices_dir: Path) -> None:
    """Create example device configurations for MikroTik and Cisco."""
    mikrotik_content = """# Example MikroTik RouterOS devices
devices:
  sw-office-01:
    host: "192.168.1.10"
    device_type: "mikrotik_routeros"
    description: "Office Switch 1"
    platform: "tile"
    model: "CRS328-24P-4S+"
    location: "Office Building A"
    tags: ["switch", "access", "office"]

  rtr-main-01:
    host: "192.168.1.1"
    device_type: "mikrotik_routeros"
    description: "Main Router"
    platform: "x86"
    model: "CCR1009-7G-1C-1S+"
    location: "Server Room"
    tags: ["router", "core", "critical"]

  ap-lobby-01:
    host: "192.168.1.20"
    device_type: "mikrotik_routeros"
    description: "Lobby Access Point"
    platform: "mipsbe"
    model: "cAP ac"
    location: "Main Lobby"
    tags: ["wireless", "access", "public"]
"""

    cisco_content = """# Example Cisco devices (when multi-vendor support is enabled)
devices:
  sw-core-01:
    host: "192.168.1.5"
    device_type: "cisco_ios"
    description: "Core Switch 1"
    model: "Catalyst 3850"
    location: "Data Center"
    tags: ["switch", "core", "cisco"]

  rtr-wan-01:
    host: "192.168.1.2"
    device_type: "cisco_ios"
    description: "WAN Router"
    model: "ISR 4431"
    location: "Server Room"
    tags: ["router", "wan", "cisco"]
"""

    mikrotik_file = devices_dir / "mikrotik.yml"
    mikrotik_file.write_text(mikrotik_content.strip() + "\n")
    console.print(f"[green]Created MikroTik devices: {mikrotik_file}[/green]")

    cisco_file = devices_dir / "cisco.yml"
    cisco_file.write_text(cisco_content.strip() + "\n")
    console.print(f"[green]Created Cisco devices: {cisco_file}[/green]")


def create_example_groups(groups_dir: Path) -> None:
    """Create device groups: tag-based and explicit members."""
    groups_content = """# Example device groups
groups:
  office_switches:
    description: "All office access switches"
    match_tags: ["switch", "office"]

  core_infrastructure:
    description: "Core network infrastructure"
    match_tags: ["core", "critical"]

  wireless_devices:
    description: "All wireless access points"
    match_tags: ["wireless", "access"]

  all_mikrotik:
    description: "All MikroTik devices"
    members: ["sw-office-01", "rtr-main-01", "ap-lobby-01"]

  all_cisco:
    description: "All Cisco devices"
    members: ["sw-core-01", "rtr-wan-01"]
"""

    groups_file = groups_dir / "main.yml"
    groups_file.write_text(groups_content.strip() + "\n")
    console.print(f"[green]Created device groups: {groups_file}[/green]")


def create_example_sequences(sequences_dir: Path) -> None:
    """Create example global command sequences (vendor-agnostic)."""
    sequences_content = """# Example command sequences
sequences:
  system_info:
    description: "Basic system information"
    commands:
      - "/system/identity/print"
      - "/system/resource/print"
      - "/system/clock/print"
      - "/system/routerboard/print"
    tags: ["info", "system"]

  interface_status:
    description: "Interface status and statistics"
    commands:
      - "/interface/print"
      - "/interface/print stats"
      - "/ip/address/print"
    tags: ["interface", "network"]

  backup_config:
    description: "Export and backup configuration"
    commands:
      - "/export compact"
      - "/system/backup/save name=auto-backup"
    tags: ["backup", "config"]
"""

    sequences_file = sequences_dir / "basic.yml"
    sequences_file.write_text(sequences_content.strip() + "\n")
    console.print(f"[green]Created command sequences: {sequences_file}[/green]")


def create_vendor_sequences(sequences_dir: Path) -> None:
    """Create vendor mapping and minimal vendor-specific sequences."""
    vendor_map_content = """# Vendor platform mapping
vendor_platforms:
  mikrotik_routeros:
    description: "MikroTik RouterOS devices"
    sequence_path: "mikrotik_routeros"
    default_files: ["common.yml"]

  cisco_ios:
    description: "Cisco IOS devices"
    sequence_path: "cisco_ios"
    default_files: ["common.yml"]
"""
    vendor_map_file = sequences_dir / "vendor.yml"
    vendor_map_file.write_text(vendor_map_content.strip() + "\n")
    console.print(f"[green]Created vendor mapping: {vendor_map_file}[/green]")

    mik_dir = sequences_dir / "mikrotik_routeros"
    mik_dir.mkdir(exist_ok=True)
    mik_common = """# Vendor-specific sequences for MikroTik RouterOS
sequences:
  system_info:
    description: "RouterOS system information (vendor-tuned)"
    commands:
      - "/system/identity/print"
      - "/system/resource/print"
      - "/system/clock/print"
    tags: ["vendor", "mikrotik"]
"""
    (mik_dir / "common.yml").write_text(mik_common.strip() + "\n")
    console.print(f"[green]Created vendor sequences: {mik_dir / 'common.yml'}[/green]")

    cisco_dir = sequences_dir / "cisco_ios"
    cisco_dir.mkdir(exist_ok=True)
    cisco_common = """# Vendor-specific sequences for Cisco IOS
sequences:
  system_info:
    description: "Cisco IOS system information (vendor-tuned)"
    commands:
      - "show version"
      - "show inventory"
      - "show interfaces status"
    tags: ["vendor", "cisco"]
"""
    (cisco_dir / "common.yml").write_text(cisco_common.strip() + "\n")
    console.print(
        f"[green]Created vendor sequences: {cisco_dir / 'common.yml'}[/green]"
    )


def register(app: typer.Typer) -> None:
  """Register the config-init command."""

  @app.command("config-init", rich_help_panel="Info & Configuration")
  def config_init(
    target_dir: Annotated[
      Path,
      typer.Argument(
        help="Directory to initialize (default: current directory)"
      ),
    ] = Path("."),
    force: Annotated[
      bool,
      typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
    verbose: Annotated[
      bool,
      typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
  ) -> None:
    """Initialize a minimal working configuration environment.

    Creates a complete starter configuration with:
    - .env file with credential templates
    - config/config.yml with core settings
    - config/devices/ with MikroTik and Cisco examples
    - config/groups/ with tag-based and explicit groups
    - config/sequences/ with global and vendor-specific sequences
    """
    setup_logging("DEBUG" if verbose else "INFO")

    target_path = Path(target_dir).resolve()
    if not target_path.exists():
      target_path.mkdir(parents=True, exist_ok=True)
      console.print(f"[cyan]Created directory: {target_path}[/cyan]")

    # Check for existing files unless force is used
    env_file = target_path / ".env"
    config_dir = target_path / "config"

    if not force:
      existing_files: list[str] = []
      if env_file.exists():
        existing_files.append(str(env_file))
      if config_dir.exists():
        existing_files.append(str(config_dir))

      if existing_files:
        console.print(
          "[yellow]Warning: The following files/directories already exist:[/yellow]"
        )
        for path in existing_files:
          console.print(f"  - {path}")
        console.print(
          "\n[yellow]Use --force to overwrite existing files.[/yellow]"
        )
        raise typer.Exit(1)

    console.print(
      f"[bold cyan]Initializing network toolkit configuration in: {target_path}[/bold cyan]"
    )
    console.print()

    # Create .env file
    create_env_file(target_path)

    # Create config directory structure
    config_dir.mkdir(exist_ok=True)
    devices_dir = config_dir / "devices"
    devices_dir.mkdir(exist_ok=True)
    groups_dir = config_dir / "groups"
    groups_dir.mkdir(exist_ok=True)
    sequences_dir = config_dir / "sequences"
    sequences_dir.mkdir(exist_ok=True)

    # Create configuration files
    create_config_yml(config_dir)
    create_example_devices(devices_dir)
    create_example_groups(groups_dir)
    create_example_sequences(sequences_dir)
    create_vendor_sequences(sequences_dir)

    console.print()
    console.print("[bold green]✓ Configuration initialization complete![/bold green]")
    console.print()
    console.print("[cyan]Next steps:[/cyan]")
    console.print("  1. Edit .env with your actual credentials")
    console.print("  2. Update config/devices/ with your actual devices")
    console.print("  3. Customize config/groups/ for your network structure")
    console.print("  4. Test connectivity: [bold]nw info sw-office-01[/bold]")
    console.print("  5. Run a command: [bold]nw run sw-office-01 system_info[/bold]")
    console.print(
      "  6. Try vendor sequences: [bold]nw run sw-core-01 system_info[/bold] (Cisco)"
    )
    console.print(
      "  7. Explore more sequences in this repo: [bold]docs/multi-vendor-support.md[/bold] and [bold]docs/examples/user_sequences/[/bold]"
    )
    console.print()
    console.print("[dim]For more help: nw --help[/dim]")
