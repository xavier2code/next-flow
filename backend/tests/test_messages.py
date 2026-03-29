"""Integration tests for message posting endpoint."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(async_client: AsyncClient) -> dict:
    """Register a user, log in, and return auth headers."""
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "message_user@example.com",
            "password": "securepassword123",
        },
    )
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "message_user@example.com", "password": "securepassword123"},
    )
    tokens = login_resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def conversation_id(
    async_client: AsyncClient, auth_headers: dict
) -> str:
    create_resp = await async_client.post(
        "/api/v1/conversations", json={}, headers=auth_headers
    )
    return create_resp.json()["data"]["id"]


async def test_send_message_returns_202(
    async_client: AsyncClient, auth_headers: dict, conversation_id: str
) -> None:
    response = await async_client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Hello, agent!"},
        headers=auth_headers,
    )
    assert response.status_code == 202


async def test_send_message_not_found(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    response = await async_client.post(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000/messages",
        json={"content": "Hello"},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_send_message_empty_content(
    async_client: AsyncClient, auth_headers: dict, conversation_id: str
) -> None:
    response = await async_client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": ""},
        headers=auth_headers,
    )
    assert response.status_code == 422
