"""Parallel execution utilities for the programmatic API."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def execute_parallel(
    items: list[T],
    func: Callable[[T], R],
    *,
    max_workers: int | None = None,
) -> list[R]:
    """Execute `func` across `items` in parallel and return results in input order."""
    if not items:
        return []

    worker_count = max_workers if max_workers is not None else len(items)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_index = {
            executor.submit(func, item): index for index, item in enumerate(items)
        }
        results_by_index: dict[int, R] = {}
        for future in as_completed(future_to_index):
            results_by_index[future_to_index[future]] = future.result()
        return [results_by_index[index] for index in range(len(items))]
