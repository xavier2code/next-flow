"""Unit tests for ConnectionManager: connect, disconnect, broadcast, multi-connection."""

from unittest.mock import AsyncMock

import pytest

from app.api.ws.connection_manager import ConnectionManager


@pytest.fixture
def manager() -> ConnectionManager:
    """Return a fresh ConnectionManager for each test."""
    return ConnectionManager()


def _make_ws() -> AsyncMock:
    """Create a mock WebSocket with an async send_json method."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------


def test_connect_adds_connection(manager: ConnectionManager) -> None:
    ws = _make_ws()
    manager.connect("user1", ws)
    assert manager.get_connection_count("user1") == 1


def test_connect_multiple_for_same_user(manager: ConnectionManager) -> None:
    ws1, ws2, ws3 = _make_ws(), _make_ws(), _make_ws()
    manager.connect("user1", ws1)
    manager.connect("user1", ws2)
    manager.connect("user1", ws3)
    assert manager.get_connection_count("user1") == 3


def test_disconnect_removes_connection(manager: ConnectionManager) -> None:
    ws1, ws2 = _make_ws(), _make_ws()
    manager.connect("user1", ws1)
    manager.connect("user1", ws2)
    manager.disconnect("user1", ws1)
    assert manager.get_connection_count("user1") == 1


def test_disconnect_removes_user_entry_when_empty(
    manager: ConnectionManager,
) -> None:
    ws = _make_ws()
    manager.connect("user1", ws)
    manager.disconnect("user1", ws)
    assert manager.get_active_user_count() == 0


def test_disconnect_idempotent(manager: ConnectionManager) -> None:
    """Disconnecting a non-tracked socket does not raise."""
    ws = _make_ws()
    manager.disconnect("user1", ws)  # should not raise
    assert manager.get_connection_count("user1") == 0


# ---------------------------------------------------------------------------
# broadcast_to_user
# ---------------------------------------------------------------------------


async def test_broadcast_to_user_sends_to_all(
    manager: ConnectionManager,
) -> None:
    ws1, ws2, ws3 = _make_ws(), _make_ws(), _make_ws()
    manager.connect("user1", ws1)
    manager.connect("user1", ws2)
    manager.connect("user1", ws3)

    event = {"type": "chunk", "data": {"content": "hello"}}
    await manager.broadcast_to_user("user1", event)

    for ws in (ws1, ws2, ws3):
        ws.send_json.assert_called_once_with(event)


async def test_broadcast_removes_dead_connections(
    manager: ConnectionManager,
) -> None:
    ws_ok = _make_ws()
    ws_dead = _make_ws()
    ws_dead.send_json.side_effect = RuntimeError("connection lost")

    manager.connect("user1", ws_ok)
    manager.connect("user1", ws_dead)

    event = {"type": "chunk", "data": {"content": "hello"}}
    await manager.broadcast_to_user("user1", event)

    # Dead connection should have been removed
    assert manager.get_connection_count("user1") == 1


async def test_broadcast_to_nonexistent_user(
    manager: ConnectionManager,
) -> None:
    """Broadcasting to a user with no connections must not raise."""
    event = {"type": "done", "data": {}}
    await manager.broadcast_to_user("unknown", event)  # should not raise


# ---------------------------------------------------------------------------
# get_active_user_count
# ---------------------------------------------------------------------------


def test_get_active_user_count(manager: ConnectionManager) -> None:
    assert manager.get_active_user_count() == 0

    manager.connect("u1", _make_ws())
    manager.connect("u2", _make_ws())
    assert manager.get_active_user_count() == 2

    # Same user, second connection -- count stays 2
    manager.connect("u1", _make_ws())
    assert manager.get_active_user_count() == 2


def test_get_connection_count_unknown_user(
    manager: ConnectionManager,
) -> None:
    assert manager.get_connection_count("nobody") == 0
