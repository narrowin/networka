"""Tests for CLI command decorators."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from network_toolkit.common.config_context import ConfigContext
from network_toolkit.common.decorators import (
    handle_command_errors,
    with_config,
    with_config_and_error_handling,
)
from network_toolkit.exceptions import ConfigurationError, NetworkToolkitError


class TestWithConfigDecorator:
    """Test the @with_config decorator."""

    def test_config_injection_default_path(self):
        """Test that ConfigContext is injected with default config path."""

        @with_config
        def mock_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            return f"Device: {device}, Config loaded: {config_ctx.is_loaded()}"

        with patch(
            "network_toolkit.common.decorators.ConfigContext"
        ) as mock_config_context:
            mock_ctx = Mock(spec=ConfigContext)
            mock_config_context.from_path.return_value = mock_ctx
            mock_ctx.is_loaded.return_value = True

            result = mock_command("router1")

            # Verify ConfigContext.from_path was called with default
            mock_config_context.from_path.assert_called_once_with(Path("config"))

            # Verify command received the context
            assert "Device: router1, Config loaded: True" == result

    def test_config_injection_explicit_path(self):
        """Test that ConfigContext is injected with explicit config path."""

        @with_config
        def mock_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            return f"Device: {device}, Path: {config_ctx.config_path}"

        with patch(
            "network_toolkit.common.decorators.ConfigContext"
        ) as mock_config_context:
            mock_ctx = Mock(spec=ConfigContext)
            mock_ctx.config_path = Path("/custom/config")
            mock_config_context.from_path.return_value = mock_ctx

            result = mock_command("router1", config_file=Path("/custom/config"))

            # Verify ConfigContext.from_path was called with custom path
            mock_config_context.from_path.assert_called_once_with(
                Path("/custom/config")
            )

            # Verify command received the context
            assert "Device: router1, Path: /custom/config" == result

    def test_config_error_handling_network_toolkit_error(self):
        """Test that NetworkToolkitError is re-raised properly."""

        @with_config
        def mock_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            return "success"

        with patch(
            "network_toolkit.common.decorators.ConfigContext"
        ) as mock_config_context:
            error = ConfigurationError("Config file not found")
            mock_config_context.from_path.side_effect = error

            with pytest.raises(ConfigurationError) as exc_info:
                mock_command("router1")

            assert str(exc_info.value) == "Config file not found"

    def test_config_error_handling_unexpected_error(self):
        """Test that unexpected errors are wrapped in ConfigurationError."""

        @with_config
        def mock_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            return "success"

        with patch(
            "network_toolkit.common.decorators.ConfigContext"
        ) as mock_config_context:
            mock_config_context.from_path.side_effect = ValueError("Unexpected error")

            with pytest.raises(ConfigurationError) as exc_info:
                mock_command("router1")

            assert "Failed to load configuration: Unexpected error" in str(
                exc_info.value
            )

    def test_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata."""

        @with_config
        def documented_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            """This is a documented command."""
            return "success"

        # Verify functools.wraps preserved metadata
        assert documented_command.__name__ == "documented_command"
        assert documented_command.__doc__ == "This is a documented command."


class TestHandleCommandErrorsDecorator:
    """Test the @handle_command_errors decorator."""

    def test_successful_execution(self):
        """Test that successful commands pass through unchanged."""

        @handle_command_errors
        def successful_command(message: str) -> str:
            return f"Success: {message}"

        result = successful_command("test")
        assert result == "Success: test"

    def test_network_toolkit_error_passthrough(self):
        """Test that NetworkToolkitError exceptions pass through."""

        @handle_command_errors
        def failing_command() -> str:
            msg = "Test error"
            raise ConfigurationError(msg)

        with pytest.raises(ConfigurationError) as exc_info:
            failing_command()

        assert str(exc_info.value) == "Test error"

    def test_unexpected_error_wrapping(self):
        """Test that unexpected errors are wrapped in NetworkToolkitError."""

        @handle_command_errors
        def error_command() -> str:
            msg = "Unexpected issue"
            raise ValueError(msg)

        with pytest.raises(NetworkToolkitError) as exc_info:
            error_command()

        assert "Unexpected error: Unexpected issue" in str(exc_info.value)

    def test_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata."""

        @handle_command_errors
        def documented_command() -> str:
            """This is a documented command."""
            return "success"

        # Verify functools.wraps preserved metadata
        assert documented_command.__name__ == "documented_command"
        assert documented_command.__doc__ == "This is a documented command."


class TestCompositeDecorator:
    """Test the @with_config_and_error_handling composite decorator."""

    def test_combines_both_decorators(self):
        """Test that composite decorator provides both config injection and error handling."""

        @with_config_and_error_handling
        def test_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            return f"Device: {device}, Config: {type(config_ctx).__name__}"

        with patch(
            "network_toolkit.common.decorators.ConfigContext"
        ) as mock_config_context:
            mock_ctx = Mock(spec=ConfigContext)
            mock_config_context.from_path.return_value = mock_ctx

            result = test_command("router1")

            # Verify both decorators are working
            mock_config_context.from_path.assert_called_once_with(Path("config"))
            assert "Device: router1, Config: Mock" == result

    def test_error_handling_with_config_injection(self):
        """Test that errors in config injection are properly handled."""

        @with_config_and_error_handling
        def test_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            return "success"

        with patch(
            "network_toolkit.common.decorators.ConfigContext"
        ) as mock_config_context:
            mock_config_context.from_path.side_effect = RuntimeError(
                "Config system failure"
            )

            with pytest.raises(ConfigurationError) as exc_info:
                test_command("router1")

            assert "Failed to load configuration: Config system failure" in str(
                exc_info.value
            )

    def test_preserves_function_metadata(self):
        """Test that composite decorator preserves original function metadata."""

        @with_config_and_error_handling
        def documented_command(
            config_ctx: ConfigContext, device: str, config_file: Path = Path("config")
        ) -> str:
            """This is a documented command."""
            return "success"

        # Verify functools.wraps preserved metadata
        assert documented_command.__name__ == "documented_command"
        assert documented_command.__doc__ == "This is a documented command."


class TestDecoratorIntegration:
    """Test decorator integration scenarios."""

    def test_multiple_parameters_preservation(self):
        """Test that decorators work with complex parameter signatures."""

        @with_config
        def complex_command(
            config_ctx: ConfigContext,
            device: str,
            commands: list[str],
            timeout: int = 30,
            *,
            verbose: bool = False,
            config_file: Path = Path("config"),
        ) -> dict:
            return {
                "device": device,
                "commands": commands,
                "timeout": timeout,
                "verbose": verbose,
                "config_loaded": config_ctx.is_loaded(),
            }

        with patch(
            "network_toolkit.common.decorators.ConfigContext"
        ) as mock_config_context:
            mock_ctx = Mock(spec=ConfigContext)
            mock_ctx.is_loaded.return_value = True
            mock_config_context.from_path.return_value = mock_ctx

            result = complex_command(
                "router1", ["show version", "show interfaces"], timeout=60, verbose=True
            )

            expected = {
                "device": "router1",
                "commands": ["show version", "show interfaces"],
                "timeout": 60,
                "verbose": True,
                "config_loaded": True,
            }

            assert result == expected
            mock_config_context.from_path.assert_called_once_with(Path("config"))
