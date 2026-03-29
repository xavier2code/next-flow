"""Integration tests for conversation CRUD + archive endpoints."""

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
    return await _make_auth_headers(async_client, "convo_user@example.com")


async def test_create_conversation(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    response = await async_client.post(
        "/api/v1/conversations", json={}, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert "id" in data
    assert data["title"] == "New Conversation"
    assert data["is_archived"] is False


async def test_list_conversations_empty(
    async_client: AsyncClient,
) -> None:
    # Use a unique user so the list is guaranteed empty
    headers = await _make_auth_headers(
        async_client, f"convo_empty_{uuid.uuid4().hex[:8]}@example.com"
    )
    response = await async_client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["has_more"] is False


async def test_list_conversations_with_data(
    async_client: AsyncClient,
) -> None:
    headers = await _make_auth_headers(
        async_client, f"convo_list_{uuid.uuid4().hex[:8]}@example.com"
    )
    for _ in range(3):
        await async_client.post(
            "/api/v1/conversations", json={}, headers=headers
        )
    response = await async_client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 3
    assert body["meta"]["has_more"] is False


async def test_get_conversation(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    create_resp = await async_client.post(
        "/api/v1/conversations", json={"title": "My Chat"}, headers=auth_headers
    )
    convo_id = create_resp.json()["data"]["id"]

    response = await async_client.get(
        f"/api/v1/conversations/{convo_id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "My Chat"


async def test_update_conversation(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    create_resp = await async_client.post(
        "/api/v1/conversations", json={}, headers=auth_headers
    )
    convo_id = create_resp.json()["data"]["id"]

    response = await async_client.patch(
        f"/api/v1/conversations/{convo_id}",
        json={"title": "Updated Title"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Updated Title"


async def test_delete_conversation(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    create_resp = await async_client.post(
        "/api/v1/conversations", json={}, headers=auth_headers
    )
    convo_id = create_resp.json()["data"]["id"]

    delete_resp = await async_client.delete(
        f"/api/v1/conversations/{convo_id}", headers=auth_headers
    )
    assert delete_resp.status_code == 204

    get_resp = await async_client.get(
        f"/api/v1/conversations/{convo_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


async def test_archive_conversation(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    create_resp = await async_client.post(
        "/api/v1/conversations", json={}, headers=auth_headers
    )
    convo_id = create_resp.json()["data"]["id"]

    response = await async_client.patch(
        f"/api/v1/conversations/{convo_id}/archive", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_archived"] is True


async def test_conversation_not_found(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    response = await async_client.get(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_unauthorized_access(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/conversations")
    assert response.status_code == 401
