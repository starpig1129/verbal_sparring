import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _setup(client, username="lb_player"):
    resp = await client.post("/api/auth/register", json={"username": username, "password": "pw"})
    return resp.json()["access_token"]


async def test_leaderboard_empty(client):
    resp = await client.get("/api/leaderboard")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


async def test_leaderboard_shows_players(client):
    await _setup(client, "topplayer")
    resp = await client.get("/api/leaderboard")
    assert resp.status_code == 200
    usernames = [e["username"] for e in resp.json()["entries"]]
    assert "topplayer" in usernames


async def test_replay_not_found(client):
    resp = await client.get(f"/api/replay/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_replay_invalid_id(client):
    resp = await client.get("/api/replay/not-a-uuid")
    assert resp.status_code == 422
