"""Integration tests for the auth API (register and login endpoints)."""

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_register_success(client) -> None:
    """Registering a new username returns 201 with a token and username."""
    resp = await client.post("/api/auth/register", json={"username": "alice", "password": "pw123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert "access_token" in data


async def test_register_duplicate(client) -> None:
    """Registering the same username twice returns 409."""
    await client.post("/api/auth/register", json={"username": "bob", "password": "pw"})
    resp = await client.post("/api/auth/register", json={"username": "bob", "password": "pw"})
    assert resp.status_code == 409


async def test_login_success(client) -> None:
    """Valid credentials return 200 with an access token."""
    await client.post("/api/auth/register", json={"username": "carol", "password": "secret"})
    resp = await client.post("/api/auth/login", json={"username": "carol", "password": "secret"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client) -> None:
    """Wrong password returns 401."""
    await client.post("/api/auth/register", json={"username": "dan", "password": "right"})
    resp = await client.post("/api/auth/login", json={"username": "dan", "password": "wrong"})
    assert resp.status_code == 401
