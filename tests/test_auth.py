"""Tests for authentication endpoints — signup, login, and /me."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import create_test_user, db_session, get_auth_headers


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    """New user can register successfully."""
    resp = await client.post(
        "/api/auth/signup",
        json={"name": "Alice", "email": "alice@test.com", "password": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert data["role"] == "user"
    assert "id" in data


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    """Duplicate email returns 409."""
    payload = {"name": "Bob", "email": "bob@test.com", "password": "secret123"}
    await client.post("/api/auth/signup", json=payload)
    resp = await client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Valid credentials return a JWT."""
    await client.post(
        "/api/auth/signup",
        json={"name": "Carol", "email": "carol@test.com", "password": "secret123"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"email": "carol@test.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Wrong password returns 401."""
    await client.post(
        "/api/auth/signup",
        json={"name": "Dave", "email": "dave@test.com", "password": "secret123"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"email": "dave@test.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient):
    """Authenticated user can hit /me."""
    signup_resp = await client.post(
        "/api/auth/signup",
        json={"name": "Eve", "email": "eve@test.com", "password": "secret123"},
    )
    user_id = signup_resp.json()["id"]
    headers = get_auth_headers(user_id)
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "eve@test.com"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    """Unauthenticated request to /me returns 401."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
