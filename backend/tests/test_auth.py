"""Tests for JWT authentication flows: register, login, refresh, logout.

Covers AUTH-01 (registration), AUTH-02 (login + JWT), AUTH-03 (refresh rotation).
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# AUTH-01 — Registration
# ---------------------------------------------------------------------------


async def test_register_success(async_client: AsyncClient) -> None:
    """POST /auth/register with valid email+password returns 201 and user data."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "display_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "newuser@example.com"
    assert data["display_name"] == "New User"
    assert "hashed_password" not in data


async def test_register_duplicate_email(
    async_client: AsyncClient,
    registered_user: dict,
) -> None:
    """POST /auth/register with an existing email returns 409 Conflict."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "anotherpassword1",
        },
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "CONFLICT"


async def test_register_short_password(async_client: AsyncClient) -> None:
    """POST /auth/register with a 7-char password returns 422."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@example.com",
            "password": "1234567",  # 7 chars — below minimum 8
        },
    )
    assert response.status_code == 422


async def test_register_missing_email(async_client: AsyncClient) -> None:
    """POST /auth/register without email returns 422 validation error."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"password": "securepassword123"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# AUTH-02 — Login
# ---------------------------------------------------------------------------


async def test_login_success(
    async_client: AsyncClient,
    registered_user: dict,
) -> None:
    """POST /auth/login with valid credentials returns 200 with tokens."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(
    async_client: AsyncClient,
    registered_user: dict,
) -> None:
    """POST /auth/login with wrong password returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "wrongpassword123",
        },
    )
    assert response.status_code == 401


async def test_login_nonexistent_user(async_client: AsyncClient) -> None:
    """POST /auth/login with unknown email returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "doesnotmatter123",
        },
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# AUTH-03 — Refresh token & rotation
# ---------------------------------------------------------------------------


async def test_refresh_token_success(
    async_client: AsyncClient,
    registered_user: dict,
) -> None:
    """POST /auth/refresh with a valid refresh token returns new token pair."""
    # Login first to get tokens
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "securepassword123",
        },
    )
    tokens = login_resp.json()

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # The new tokens must differ from the originals
    assert data["refresh_token"] != tokens["refresh_token"]


async def test_refresh_token_rotation(
    async_client: AsyncClient,
    registered_user: dict,
) -> None:
    """Using the same refresh token twice returns 401 on the second attempt."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "securepassword123",
        },
    )
    tokens = login_resp.json()
    old_refresh = tokens["refresh_token"]

    # First refresh should succeed
    resp1 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert resp1.status_code == 200

    # Second use of the same refresh token should fail (rotation)
    resp2 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert resp2.status_code == 401


async def test_refresh_expired_token(async_client: AsyncClient) -> None:
    """POST /auth/refresh with an invalid/expired token returns 401."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "this.is.not.valid"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def test_logout_success(
    async_client: AsyncClient,
    registered_user: dict,
) -> None:
    """POST /auth/logout with a valid access token returns 200."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "securepassword123",
        },
    )
    tokens = login_resp.json()

    response = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Protected endpoint
# ---------------------------------------------------------------------------


async def test_access_protected_endpoint(
    async_client: AsyncClient,
    registered_user: dict,
) -> None:
    """GET /auth/me with a valid access token returns user data."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "securepassword123",
        },
    )
    tokens = login_resp.json()

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"


async def test_access_protected_no_token(async_client: AsyncClient) -> None:
    """GET /auth/me without a token returns 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
