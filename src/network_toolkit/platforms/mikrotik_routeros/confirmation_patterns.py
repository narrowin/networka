"""MikroTik RouterOS specific confirmation patterns."""

from network_toolkit.common.interactive_confirmation import ConfirmationPattern

# MikroTik RouterOS confirmation patterns
MIKROTIK_REBOOT = ConfirmationPattern(
    prompt="Reboot, yes? [y/N]:", response="y", is_reboot_operation=True
)

MIKROTIK_PACKAGE_DOWNGRADE = ConfirmationPattern(
    prompt="Router will be rebooted. Continue? [y/N]:",
    response="y",
    is_reboot_operation=True,
)

MIKROTIK_ROUTERBOARD_UPGRADE = ConfirmationPattern(
    prompt="Do you really want to upgrade firmware? [y/n]",
    response="y",
    is_reboot_operation=False,  # The upgrade itself doesn't reboot, but usually followed by reboot
)

MIKROTIK_SYSTEM_RESET = ConfirmationPattern(
    prompt="Dangerous! Reset anyway? [y/N]:", response="y", is_reboot_operation=True
)
