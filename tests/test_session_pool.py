# SPDX-License-Identifier: MIT
"""Tests for session_pool module."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from network_toolkit.session_pool import SessionPool


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock DeviceSession."""
    session = MagicMock()
    session.disconnect = MagicMock()
    return session


@pytest.fixture
def pool() -> SessionPool:
    """Create a fresh SessionPool."""
    return SessionPool()


class TestSessionPoolBasicOperations:
    """Test basic get/set/remove operations."""

    def test_get_returns_none_for_missing(self, pool: SessionPool) -> None:
        assert pool.get("nonexistent") is None

    def test_get_returns_session_when_present(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        pool["router1"] = mock_session
        assert pool.get("router1") is mock_session

    def test_setitem_stores_session(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        pool["router1"] = mock_session
        assert "router1" in pool
        assert len(pool) == 1

    def test_getitem_raises_keyerror_for_missing(self, pool: SessionPool) -> None:
        with pytest.raises(KeyError):
            _ = pool["nonexistent"]

    def test_getitem_returns_session(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        pool["router1"] = mock_session
        assert pool["router1"] is mock_session

    def test_remove_returns_and_deletes(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        pool["router1"] = mock_session
        removed = pool.remove("router1")
        assert removed is mock_session
        assert "router1" not in pool

    def test_remove_returns_none_for_missing(self, pool: SessionPool) -> None:
        assert pool.remove("nonexistent") is None

    def test_contains_checks_presence(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        assert "router1" not in pool
        pool["router1"] = mock_session
        assert "router1" in pool

    def test_len_returns_count(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        assert len(pool) == 0
        pool["router1"] = mock_session
        pool["router2"] = mock_session
        assert len(pool) == 2

    def test_keys_returns_device_names(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        pool["router1"] = mock_session
        pool["switch1"] = mock_session
        keys = pool.keys()
        assert set(keys) == {"router1", "switch1"}


class TestSessionPoolCleanup:
    """Test clear and close_all operations."""

    def test_clear_removes_all_sessions(
        self, pool: SessionPool, mock_session: MagicMock
    ) -> None:
        pool["router1"] = mock_session
        pool["router2"] = mock_session
        pool.clear()
        assert len(pool) == 0

    def test_close_all_disconnects_all_sessions(self, pool: SessionPool) -> None:
        session1 = MagicMock()
        session2 = MagicMock()
        pool["router1"] = session1
        pool["router2"] = session2

        pool.close_all()

        session1.disconnect.assert_called_once()
        session2.disconnect.assert_called_once()
        assert len(pool) == 0

    def test_close_all_handles_disconnect_failure(
        self, pool: SessionPool, caplog: pytest.LogCaptureFixture
    ) -> None:
        session1 = MagicMock()
        session1.disconnect.side_effect = Exception("Connection lost")
        session2 = MagicMock()
        pool["router1"] = session1
        pool["router2"] = session2

        with caplog.at_level(logging.WARNING):
            pool.close_all()

        # Should still clear pool despite failure
        assert len(pool) == 0
        # Should log warning about failed disconnect
        assert "router1" in caplog.text
        assert "Failed to disconnect" in caplog.text

    def test_close_all_logs_summary_of_failures(
        self, pool: SessionPool, caplog: pytest.LogCaptureFixture
    ) -> None:
        session1 = MagicMock()
        session1.disconnect.side_effect = Exception("Err1")
        session2 = MagicMock()
        session2.disconnect.side_effect = Exception("Err2")
        pool["router1"] = session1
        pool["router2"] = session2

        with caplog.at_level(logging.WARNING):
            pool.close_all()

        # Both should be logged in summary
        assert "Sessions failed to disconnect cleanly" in caplog.text


class TestSessionPoolThreadSafety:
    """Test thread-safe concurrent access."""

    def test_concurrent_set_operations(self, pool: SessionPool) -> None:
        """Multiple threads can safely add sessions."""

        def add_session(name: str) -> None:
            session = MagicMock()
            pool[name] = session

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(add_session, f"device{i}") for i in range(100)]
            for f in futures:
                f.result()

        assert len(pool) == 100

    def test_concurrent_get_and_set(self, pool: SessionPool) -> None:
        """Concurrent reads and writes don't corrupt state."""
        pool["shared"] = MagicMock()
        errors: list[Exception] = []

        def reader() -> None:
            for _ in range(100):
                try:
                    pool.get("shared")
                except Exception as e:
                    errors.append(e)

        def writer() -> None:
            for i in range(100):
                try:
                    pool[f"device{i}"] = MagicMock()
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_remove_during_iteration(self, pool: SessionPool) -> None:
        """Remove during keys() iteration is safe."""
        for i in range(10):
            pool[f"device{i}"] = MagicMock()

        def remover() -> None:
            for i in range(10):
                pool.remove(f"device{i}")

        def lister() -> None:
            for _ in range(10):
                pool.keys()

        t1 = threading.Thread(target=remover)
        t2 = threading.Thread(target=lister)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(pool) == 0

    def test_concurrent_close_all(self, pool: SessionPool) -> None:
        """Multiple close_all calls are safe."""
        for i in range(10):
            session = MagicMock()
            pool[f"device{i}"] = session

        def close_all() -> None:
            pool.close_all()

        threads = [threading.Thread(target=close_all) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(pool) == 0
