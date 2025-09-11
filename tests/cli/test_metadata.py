"""Tests for CLI metadata and command configuration."""

import pytest

from network_toolkit.cli.metadata import (
    CommandCategory,
    CommandMetadata,
    validate_command_list,
)


class TestCommandMetadata:
    """Test the CommandMetadata dataclass."""

    def test_valid_metadata_creation(self):
        """Test creating valid command metadata."""
        metadata = CommandMetadata(
            name="test_command",
            category=CommandCategory.EXECUTING_OPERATIONS,
            description="Test command description",
            order=10,
        )

        assert metadata.name == "test_command"
        assert metadata.category == CommandCategory.EXECUTING_OPERATIONS
        assert metadata.description == "Test command description"
        assert metadata.order == 10
        assert metadata.hidden is False

    def test_metadata_defaults(self):
        """Test default values for optional fields."""
        metadata = CommandMetadata(
            name="test",
            category=CommandCategory.INFO_CONFIGURATION,
            description="Test description",
        )

        assert metadata.order == 50  # Default
        assert metadata.hidden is False  # Default

    def test_empty_name_validation(self):
        """Test that empty command names are rejected."""
        with pytest.raises(ValueError, match="Command name cannot be empty"):
            CommandMetadata(
                name="",
                category=CommandCategory.EXECUTING_OPERATIONS,
                description="Test",
            )

    def test_missing_description_validation(self):
        """Test that non-hidden commands require descriptions."""
        with pytest.raises(ValueError, match="must have a description unless hidden"):
            CommandMetadata(
                name="test",
                category=CommandCategory.EXECUTING_OPERATIONS,
                description="",
            )

    def test_hidden_command_no_description_allowed(self):
        """Test that hidden commands can have empty descriptions."""
        metadata = CommandMetadata(
            name="hidden_test",
            category=CommandCategory.HIDDEN,
            description="",
            hidden=True,
        )

        assert metadata.name == "hidden_test"
        assert metadata.hidden is True

    def test_negative_order_validation(self):
        """Test that negative order values are rejected."""
        with pytest.raises(ValueError, match="order must be non-negative"):
            CommandMetadata(
                name="test",
                category=CommandCategory.EXECUTING_OPERATIONS,
                description="Test",
                order=-1,
            )


class TestCommandListValidation:
    """Test validation of command lists."""

    def test_valid_command_list(self):
        """Test validation of a valid command list."""
        commands = [
            CommandMetadata("cmd1", CommandCategory.EXECUTING_OPERATIONS, "Desc 1"),
            CommandMetadata("cmd2", CommandCategory.INFO_CONFIGURATION, "Desc 2"),
        ]

        # Should not raise any exception
        validate_command_list(commands)

    def test_duplicate_names_rejected(self):
        """Test that duplicate command names are rejected."""
        commands = [
            CommandMetadata(
                "duplicate", CommandCategory.EXECUTING_OPERATIONS, "Desc 1"
            ),
            CommandMetadata("duplicate", CommandCategory.INFO_CONFIGURATION, "Desc 2"),
        ]

        with pytest.raises(ValueError, match="Duplicate command names found"):
            validate_command_list(commands)

    def test_hidden_category_validation(self):
        """Test that HIDDEN category commands must be marked hidden."""
        commands = [
            CommandMetadata(
                "hidden_cmd",
                CommandCategory.HIDDEN,
                "Description",
                hidden=False,  # This should trigger validation error
            )
        ]

        with pytest.raises(
            ValueError, match="in HIDDEN category must have hidden=True"
        ):
            validate_command_list(commands)


class TestCommandCategory:
    """Test the CommandCategory enum."""

    def test_category_values(self):
        """Test that category enum has expected values."""
        assert CommandCategory.EXECUTING_OPERATIONS.value == "Executing Operations"
        assert CommandCategory.VENDOR_SPECIFIC.value == "Vendor-Specific Operations"
        assert CommandCategory.INFO_CONFIGURATION.value == "Info & Configuration"
        assert CommandCategory.HIDDEN.value == "Hidden"

    def test_all_categories_present(self):
        """Test that we have all expected categories."""
        expected_categories = {
            "EXECUTING_OPERATIONS",
            "VENDOR_SPECIFIC",
            "INFO_CONFIGURATION",
            "HIDDEN",
        }

        actual_categories = {category.name for category in CommandCategory}
        assert actual_categories == expected_categories
