"""Parallel execution utilities for network operations."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def execute_parallel(
    items: list[T],
    func: Callable[[T], R],
    max_workers: int | None = None,
) -> list[R]:
    """
    Execute a function in parallel across a list of items using threads.

    Parameters
    ----------
    items : list[T]
        List of items to process
    func : Callable[[T], R]
        Function to execute for each item
    max_workers : int | None
        Maximum number of threads to use. Defaults to len(items).

    Returns
    -------
    list[R]
        List of results in the same order as the input items.
    """
    if not items:
        return []

    workers = max_workers if max_workers is not None else len(items)
    results: list[R] = [None] * len(items)  # type: ignore[list-item]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(func, item): index for index, item in enumerate(items)
        }

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            results[index] = future.result()

    # `results` is fully populated because we submitted exactly one future per item.
    return results
