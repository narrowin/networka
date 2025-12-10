# SPDX-License-Identifier: MIT
"""Interactive credential input utilities."""

from __future__ import annotations

import getpass
from typing import NamedTuple

import typer


class InteractiveCredentials(NamedTuple):
    """Container for interactively entered credentials."""

    username: str
    password: str


def prompt_for_credentials(
    username_prompt: str = "Username",
    password_prompt: str = "Password",
    default_username: str | None = None,
) -> InteractiveCredentials:
    """
    Securely prompt for username and password.

    Parameters
    ----------
    username_prompt : str
        Prompt text for username input
    password_prompt : str
        Prompt text for password input
    default_username : str | None
        Default username to use (can be overridden)

    Returns
    -------
    InteractiveCredentials
        Named tuple containing username and password

    Examples
    --------
    >>> creds = prompt_for_credentials("Enter username", "Enter password", "admin")
    >>> print(f"User: {creds.username}")
    """
    # Prompt for username with optional default
    if default_username:
        username = typer.prompt(
            f"{username_prompt} [{default_username}]",
            default=default_username,
            show_default=False,
        )
    else:
        username = typer.prompt(username_prompt)

    # Securely prompt for password (hidden input)
    password = getpass.getpass(f"{password_prompt}: ")

    if not username.strip():
        msg = "Username cannot be empty"
        raise typer.BadParameter(msg)

    if not password:
        msg = "Password cannot be empty"
        raise typer.BadParameter(msg)

    return InteractiveCredentials(username.strip(), password)


def confirm_credentials(credentials: InteractiveCredentials) -> bool:
    """
    Ask user to confirm the entered credentials.

    Parameters
    ----------
    credentials : InteractiveCredentials
        The credentials to confirm

    Returns
    -------
    bool
        True if user confirms, False otherwise
    """
    return typer.confirm(
        f"Use username '{credentials.username}' with provided password?"
    )
