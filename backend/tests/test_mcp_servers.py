"""Integration tests for MCP server Admin API endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.main import app
from app.api.deps import get_mcp_manager


async def _make_auth_headers(async_client: AsyncClient, email: str) -> dict:
    """Register a user (tolerate 409) and return auth headers."""
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepassword123"},
    )
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepassword123"},
    )
    tokens = login_resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def auth_headers(async_client: AsyncClient) -> dict:
    return await _make_auth_headers(async_client, "mcp_user@example.com")


@pytest.fixture
async def mock_mcp_manager():
    """Replace get_mcp_manager dependency with a mock.

    Uses app.dependency_overrides directly (same pattern as conftest.py
    overrides for get_db and get_redis). Do NOT use async_client._transport.app.
    """
    manager = MagicMock()
    manager.connect_all = AsyncMock()
    manager.disconnect_all = AsyncMock()
    manager.start_health_check = AsyncMock()
    manager.stop_health_check = AsyncMock()
    manager.connect_server = AsyncMock()
    manager.disconnect_server = AsyncMock()
    manager.clients = {}

    app.dependency_overrides[get_mcp_manager] = lambda: manager
    app.state.mcp_manager = manager

    yield manager

    # Cleanup
    if get_mcp_manager in app.dependency_overrides:
        del app.dependency_overrides[get_mcp_manager]


async def test_register_server_returns_201(
    async_client: AsyncClient, auth_headers: dict, mock_mcp_manager: MagicMock
) -> None:
    """POST /api/v1/mcp-servers returns 201 with status=connecting."""
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "test-server", "url": "http://localhost:8080"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "test-server"
    assert data["status"] == "connecting"
    assert data["url"] == "http://localhost:8080"
    assert data["transport_type"] == "streamable_http"


async def test_list_servers_returns_paginated(
    async_client: AsyncClient, auth_headers: dict, mock_mcp_manager: MagicMock
) -> None:
    """GET /api/v1/mcp-servers returns paginated list."""
    # Register 2 servers
    r1 = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "server-1", "url": "http://localhost:8081"},
        headers=auth_headers,
    )
    assert r1.status_code == 201
    r2 = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "server-2", "url": "http://localhost:8082"},
        headers=auth_headers,
    )
    assert r2.status_code == 201

    response = await async_client.get(
        "/api/v1/mcp-servers",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    names = [s["name"] for s in body["data"]]
    assert "server-1" in names
    assert "server-2" in names
    assert body["meta"]["has_more"] is False


async def test_get_server_detail(
    async_client: AsyncClient, auth_headers: dict, mock_mcp_manager: MagicMock
) -> None:
    """GET /api/v1/mcp-servers/{id} returns server detail."""
    create_resp = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "detail-server", "url": "http://localhost:8083"},
        headers=auth_headers,
    )
    server_id = create_resp.json()["data"]["id"]

    response = await async_client.get(
        f"/api/v1/mcp-servers/{server_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "detail-server"


async def test_get_server_not_found(
    async_client: AsyncClient, auth_headers: dict, mock_mcp_manager: MagicMock
) -> None:
    """GET /api/v1/mcp-servers/{id} returns 404 for nonexistent server."""
    fake_id = str(uuid.uuid4())
    response = await async_client.get(
        f"/api/v1/mcp-servers/{fake_id}",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_update_server(
    async_client: AsyncClient, auth_headers: dict, mock_mcp_manager: MagicMock
) -> None:
    """PATCH /api/v1/mcp-servers/{id} updates name and triggers reconnect."""
    create_resp = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "original-name", "url": "http://localhost:8084"},
        headers=auth_headers,
    )
    server_id = create_resp.json()["data"]["id"]

    response = await async_client.patch(
        f"/api/v1/mcp-servers/{server_id}",
        json={"name": "updated-name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "updated-name"
    assert response.json()["data"]["status"] == "connecting"


async def test_delete_server(
    async_client: AsyncClient, auth_headers: dict, mock_mcp_manager: MagicMock
) -> None:
    """DELETE /api/v1/mcp-servers/{id} returns 204 and removes server."""
    create_resp = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "delete-me", "url": "http://localhost:8085"},
        headers=auth_headers,
    )
    server_id = create_resp.json()["data"]["id"]

    delete_resp = await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 204

    # Verify server is gone
    get_resp = await async_client.get(
        f"/api/v1/mcp-servers/{server_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


async def test_list_server_tools(
    async_client: AsyncClient, auth_headers: dict, mock_mcp_manager: MagicMock
) -> None:
    """GET /api/v1/mcp-servers/{id}/tools returns discovered tools."""
    # Ensure tool_registry exists on app.state (not set when lifespan is skipped)
    if not hasattr(app.state, "tool_registry") or app.state.tool_registry is None:
        from app.services.tool_registry import ToolRegistry
        app.state.tool_registry = ToolRegistry()

    create_resp = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "tool-server", "url": "http://localhost:8086"},
        headers=auth_headers,
    )
    server_id = create_resp.json()["data"]["id"]

    # Manually add tools to the tool registry using the app's state
    registry = app.state.tool_registry
    registry.register(
        name="mcp__tool-server__search",
        schema={"type": "object", "properties": {"query": {"type": "string"}}},
        handler=AsyncMock(),
    )
    registry.register(
        name="mcp__tool-server__fetch",
        schema={"type": "object", "properties": {"url": {"type": "string"}}},
        handler=AsyncMock(),
    )

    response = await async_client.get(
        f"/api/v1/mcp-servers/{server_id}/tools",
        headers=auth_headers,
    )
    assert response.status_code == 200
    tools = response.json()["data"]
    assert len(tools) == 2
    tool_names = [t["name"] for t in tools]
    assert "search" in tool_names
    assert "fetch" in tool_names

    # Cleanup registered tools
    registry.unregister("mcp__tool-server__")


async def test_unauthenticated_returns_401(async_client: AsyncClient) -> None:
    """POST /api/v1/mcp-servers without auth returns 401."""
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json={"name": "unauth-server", "url": "http://localhost:8087"},
    )
    assert response.status_code == 401
