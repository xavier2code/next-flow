"""Integration tests for settings endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(async_client: AsyncClient) -> dict:
    """Register a user, log in, and return auth headers."""
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "settings_user@example.com",
            "password": "securepassword123",
        },
    )
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "settings_user@example.com", "password": "securepassword123"},
    )
    tokens = login_resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_get_settings_default(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    response = await async_client.get("/api/v1/settings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["preferences"] == {}


async def test_update_settings(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    response = await async_client.patch(
        "/api/v1/settings",
        json={"preferences": {"default_model": "gpt-4o"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["preferences"] == {"default_model": "gpt-4o"}


async def test_get_system_config(
    async_client: AsyncClient, auth_headers: dict
) -> None:
    response = await async_client.get("/api/v1/settings/system", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "openai" in data["available_providers"]
    assert data["default_provider"] is not None
    assert data["default_model"] is not None
