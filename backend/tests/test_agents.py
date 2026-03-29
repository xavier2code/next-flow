"""Integration tests for agent CRUD endpoints."""

import uuid

import pytest
from httpx import AsyncClient


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
    return await _make_auth_headers(async_client, "agent_user@example.com")


async def test_create_agent(async_client: AsyncClient, auth_headers: dict) -> None:
    response = await async_client.post(
        "/api/v1/agents",
        json={"name": "Test Agent", "system_prompt": "You are a helpful assistant."},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert "id" in data
    assert data["name"] == "Test Agent"
    assert data["system_prompt"] == "You are a helpful assistant."


async def test_list_agents(async_client: AsyncClient) -> None:
    headers = await _make_auth_headers(
        async_client, f"agent_list_{uuid.uuid4().hex[:8]}@example.com"
    )
    response = await async_client.get("/api/v1/agents", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["has_more"] is False


async def test_get_agent(async_client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await async_client.post(
        "/api/v1/agents",
        json={"name": "Fetch Agent"},
        headers=auth_headers,
    )
    agent_id = create_resp.json()["data"]["id"]

    response = await async_client.get(
        f"/api/v1/agents/{agent_id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Fetch Agent"


async def test_update_agent(async_client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await async_client.post(
        "/api/v1/agents",
        json={"name": "Original Name"},
        headers=auth_headers,
    )
    agent_id = create_resp.json()["data"]["id"]

    response = await async_client.patch(
        f"/api/v1/agents/{agent_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Updated Name"


async def test_delete_agent(async_client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await async_client.post(
        "/api/v1/agents",
        json={"name": "Delete Me"},
        headers=auth_headers,
    )
    agent_id = create_resp.json()["data"]["id"]

    delete_resp = await async_client.delete(
        f"/api/v1/agents/{agent_id}", headers=auth_headers
    )
    assert delete_resp.status_code == 204

    get_resp = await async_client.get(
        f"/api/v1/agents/{agent_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


async def test_agent_with_llm_config(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    response = await async_client.post(
        "/api/v1/agents",
        json={
            "name": "Configured Agent",
            "llm_config": {"provider": "ollama", "model": "llama3"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["llm_config"] == {"provider": "ollama", "model": "llama3"}
