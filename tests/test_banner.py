"""Tests for banner functionality."""

from __future__ import annotations

from unittest.mock import patch

from network_toolkit.banner import BANNER, show_banner


def test_banner_content():
    """Test that the banner contains expected content."""
    assert "NETWORKA" in BANNER
    assert "█" in BANNER  # Contains ASCII art characters
    assert len(BANNER.strip()) > 100  # Reasonable size check


def test_show_banner():
    """Test that show_banner displays the banner with welcome messages."""
    with patch("network_toolkit.banner.CommandContext") as mock_ctx_class:
        mock_ctx = mock_ctx_class.return_value

        show_banner()

        # Should have called print_info 3 times (banner + 2 welcome messages)
        assert mock_ctx.print_info.call_count == 3

        # Check the banner was printed
        banner_call = mock_ctx.print_info.call_args_list[0][0][0]
        assert "NETWORKA" in banner_call

        # Check welcome messages
        welcome_call = mock_ctx.print_info.call_args_list[1][0][0]
        assert "Welcome to Networka" in welcome_call

        help_call = mock_ctx.print_info.call_args_list[2][0][0]
        assert "nw --help" in help_call
