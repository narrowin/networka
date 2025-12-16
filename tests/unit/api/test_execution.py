"""Tests for parallel execution utilities."""

import pytest

from network_toolkit.api.execution import execute_parallel


def test_execute_parallel_empty_list():
    """Test that execute_parallel returns empty list for empty input."""
    result = execute_parallel([], lambda x: x)
    assert result == []


def test_execute_parallel_single_item():
    """Test execute_parallel with a single item."""
    result = execute_parallel([1], lambda x: x * 2)
    assert result == [2]


def test_execute_parallel_multiple_items():
    """Test execute_parallel with multiple items."""
    items = [1, 2, 3, 4, 5]
    result = execute_parallel(items, lambda x: x * 2)
    assert result == [2, 4, 6, 8, 10]


def test_execute_parallel_exception_propagation():
    """Test that exceptions in worker functions are propagated."""

    def failing_func(x):
        if x == 3:
            msg = "Test error"
            raise ValueError(msg)
        return x

    items = [1, 2, 3, 4]

    with pytest.raises(ValueError, match="Test error"):
        execute_parallel(items, failing_func)


def test_execute_parallel_max_workers():
    """Test execute_parallel with max_workers parameter."""
    # This test mainly ensures the parameter is accepted and code runs.
    # Verifying actual thread count is hard without mocking ThreadPoolExecutor.
    items = list(range(10))
    result = execute_parallel(items, lambda x: x, max_workers=2)
    assert result == items


def test_execute_parallel_preserves_input_order():
    """Test that results are returned in input order."""
    items = [3, 1, 2]
    result = execute_parallel(items, lambda x: x)
    assert result == items
