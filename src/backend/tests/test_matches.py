"""Integration tests for the matches REST API."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_and_token(client: AsyncClient, username: str = "player1") -> str:
    """Register a new player and return the access token.

    Args:
        client: The async HTTP test client.
        username: Unique username to register.

    Returns:
        The JWT access token string from the registration response.
    """
    resp = await client.post("/api/auth/register", json={"username": username, "password": "pw"})
    return resp.json()["access_token"]


async def test_create_npc_match(client: AsyncClient) -> None:
    """Creating a match with opponent='npc' returns 201 with is_npc=True."""
    token = await _register_and_token(client, "alice2")
    resp = await client.post(
        "/api/matches",
        json={"opponent": "npc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_npc"] is True
    assert "match_id" in data


async def test_create_match_opponent_not_found(client: AsyncClient) -> None:
    """Creating a match against a non-existent username returns 404."""
    token = await _register_and_token(client, "bob2")
    resp = await client.post(
        "/api/matches",
        json={"opponent": "nonexistent"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_create_match_vs_human(client: AsyncClient) -> None:
    """Creating a match against a registered opponent returns 201 with is_npc=False."""
    t1 = await _register_and_token(client, "player_a")
    await client.post("/api/auth/register", json={"username": "player_b", "password": "pw"})
    resp = await client.post(
        "/api/matches",
        json={"opponent": "player_b"},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_npc"] is False


async def test_create_match_unauthorized(client: AsyncClient) -> None:
    """Calling the endpoint without an Authorization header returns 401."""
    resp = await client.post(
        "/api/matches",
        json={"opponent": "npc"},
    )
    assert resp.status_code == 401


async def test_create_match_self(client: AsyncClient) -> None:
    """Creating a match against yourself returns 400."""
    token = await _register_and_token(client, "selfplayer")
    resp = await client.post(
        "/api/matches",
        json={"opponent": "selfplayer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
