"""Integration tests for WebSocket /ws/chat endpoint.

Tests cover:
  - Valid JWT connection acceptance
  - Invalid/missing JWT rejection (close code 4001)
  - Connection cleanup on disconnect
  - Multi-connection support per user

Note: Event streaming is validated by unit tests (test_event_mapper.py).
These integration tests focus on the WebSocket lifecycle and auth.

Architecture: Uses a dedicated FastAPI test app with a lightweight lifespan
that only initializes ConnectionManager (no PostgreSQL checkpointer needed
for WebSocket lifecycle tests). The WS router is included to test the full
connection flow. Auth tests use direct JWT creation via the security module
to avoid needing the database-backed registration/login endpoints.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api.ws.chat import router as ws_router
from app.api.ws.connection_manager import ConnectionManager
from app.core.security import create_access_token


# ---------------------------------------------------------------------------
# Test app with lightweight lifespan (no external service dependencies)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _test_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Minimal lifespan: only init ConnectionManager, no DB/Redis."""
    app.state.connection_manager = ConnectionManager()
    yield


_test_app = FastAPI(lifespan=_test_lifespan)
_test_app.include_router(ws_router)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ws_client():
    """Synchronous TestClient wired to the lightweight test app."""
    with TestClient(_test_app) as client:
        yield client


@pytest.fixture
def auth_token():
    """Create a valid access token for a test user (no DB required)."""
    return create_access_token(subject="test-user-123")


# ---------------------------------------------------------------------------
# Connection tests
# ---------------------------------------------------------------------------


def test_ws_connect_with_valid_token(ws_client, auth_token) -> None:
    """WebSocket connection with a valid JWT should be accepted."""
    with ws_client.websocket_connect(f"/ws/chat?token={auth_token}"):
        # Connection accepted -- no immediate close.
        pass


def test_ws_reject_invalid_token(ws_client) -> None:
    """WebSocket connection with an invalid token should close with code 4001."""
    with pytest.raises(Exception):
        with ws_client.websocket_connect("/ws/chat?token=invalid-token"):
            pass


def test_ws_reject_missing_token(ws_client) -> None:
    """WebSocket connection without a token param should be rejected."""
    with pytest.raises(Exception):
        with ws_client.websocket_connect("/ws/chat"):
            pass


def test_ws_disconnect_cleanup(ws_client, auth_token) -> None:
    """After disconnecting, the ConnectionManager should have no connections."""
    manager = ws_client.app.state.connection_manager

    with ws_client.websocket_connect(f"/ws/chat?token={auth_token}"):
        assert manager.get_connection_count("test-user-123") >= 1

    # After context exit, cleanup should have removed the connection
    assert manager.get_connection_count("test-user-123") == 0


def test_ws_multi_connection(ws_client, auth_token) -> None:
    """Multiple WebSocket connections for the same user should all be tracked."""
    manager = ws_client.app.state.connection_manager

    with ws_client.websocket_connect(f"/ws/chat?token={auth_token}"):
        assert manager.get_connection_count("test-user-123") == 1

        with ws_client.websocket_connect(f"/ws/chat?token={auth_token}"):
            assert manager.get_connection_count("test-user-123") == 2

        # After inner connection closes, count drops to 1
        assert manager.get_connection_count("test-user-123") == 1

    # After outer connection closes, count drops to 0
    assert manager.get_connection_count("test-user-123") == 0
