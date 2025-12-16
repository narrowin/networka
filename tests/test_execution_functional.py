"""Functional tests for parallel execution."""

import time

import pytest

from network_toolkit.api.execution import execute_parallel


def test_parallel_execution_performance():
    """
    Verify that execute_parallel actually runs tasks concurrently.

    We simulate a blocking network operation with time.sleep().
    If running sequentially, 5 items * 0.1s = 0.5s.
    If running in parallel, it should take slightly more than 0.1s.
    """

    def simulated_blocking_op(item: str) -> str:
        time.sleep(0.1)
        return f"processed-{item}"

    items = [f"item-{i}" for i in range(5)]

    start_time = time.time()
    results = execute_parallel(items, simulated_blocking_op, max_workers=5)
    duration = time.time() - start_time

    # Verify results are correct
    assert len(results) == 5
    for i in range(5):
        assert f"processed-item-{i}" in results

    # Verify speedup (allow some overhead, but must be significantly faster than sequential)
    # Sequential would be >= 0.5s. Parallel should be closer to 0.1s.
    # We set a generous upper bound of 0.3s to account for CI slowness.
    assert duration < 0.4, (
        f"Execution took {duration}s, expected < 0.4s for parallel execution"
    )


def test_parallel_execution_large_batch():
    """Test with a larger batch of items to ensure stability."""

    def simple_op(x: int) -> int:
        return x * x

    # 100 items
    items = list(range(100))
    results = execute_parallel(items, simple_op, max_workers=10)

    assert len(results) == 100
    assert sum(results) == sum(x * x for x in range(100))


def test_parallel_execution_mixed_failures():
    """
    Test behavior when some tasks fail.
    Currently execute_parallel fails fast on the first exception encountered
    during result retrieval.
    """

    def op_with_random_failure(x: int) -> int:
        if x == 50:
            msg = "Boom"
            raise ValueError(msg)
        return x

    items = list(range(100))

    with pytest.raises(ValueError, match="Boom"):
        execute_parallel(items, op_with_random_failure)
