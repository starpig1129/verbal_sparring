"""WebSocket battle endpoint integration tests.

Uses ``starlette.testclient.TestClient`` (synchronous) so the test functions
themselves are plain ``def``, while the DB-setup fixture is async (session
scope) to align with the session-scoped event loop configured in pytest.ini.
"""

import json

import pytest_asyncio
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.backend.core.database import get_session
from src.backend.main import app
from src.backend.tests.conftest import RESOLVED_URL


async def _ws_test_session():
    """Yield a fresh NullPool async session for each WS endpoint call.

    A new engine is created per invocation so asyncpg connections are
    always bound to the currently active event loop, avoiding the
    "Future attached to a different loop" error that arises when pooled
    connections are reused across loop boundaries.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    eng = create_async_engine(RESOLVED_URL, poolclass=NullPool)
    factory = async_sessionmaker(eng, expire_on_commit=False)
    async with factory() as session:
        yield session
    await eng.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ws_db_setup(test_engine):
    """Ensure the schema exists before any WS test runs.

    The ``test_engine`` dependency guarantees ``Base.metadata.create_all``
    has been called.  The dependency override is set here and left in place
    for the duration of the test session; individual test functions also set
    it explicitly so that any ``app.dependency_overrides.clear()`` from
    other fixtures does not break WS tests.
    """
    app.dependency_overrides[get_session] = _ws_test_session
    yield


def _setup_player_and_match(client: TestClient, username: str = "ws_player") -> tuple[str, str]:
    """Register a player, log in, and create an NPC match.

    Args:
        client: A live TestClient connected to the app.
        username: Username to register; must be unique within the test session.

    Returns:
        Tuple of (access_token, match_id).
    """
    reg = client.post("/api/auth/register", json={"username": username, "password": "pw"})
    token = reg.json()["access_token"]
    match = client.post(
        "/api/matches",
        json={"opponent": "npc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, match.json()["match_id"]


def test_websocket_connect_and_system_message():
    """Connecting to the battle WS should immediately broadcast a system message."""
    app.dependency_overrides[get_session] = _ws_test_session

    with patch(
        "src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock
    ) as mock_ref, patch(
        "src.backend.services.npc.agent._call_ollama", new_callable=AsyncMock
    ) as mock_npc:
        mock_ref.return_value = (
            '{"damage": 15, "referee_comment": "不錯", "display_text": "你很差！"}'
        )
        mock_npc.return_value = "你的臉跟你的攻擊一樣難看"

        with TestClient(app) as client:
            token, match_id = _setup_player_and_match(client, "ws_tester")
            with client.websocket_connect(
                f"/ws/battle/{match_id}/ws_tester?token={token}"
            ) as ws:
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "system"
                assert "ws_tester" in msg["message"]


def test_websocket_attack_reduces_hp():
    """Sending an attack message should reduce the target's HP by the referee damage."""
    app.dependency_overrides[get_session] = _ws_test_session

    with patch(
        "src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock
    ) as mock_ref, patch(
        "src.backend.services.npc.agent._call_ollama", new_callable=AsyncMock
    ) as mock_npc:
        mock_ref.return_value = (
            '{"damage": 20, "referee_comment": "猛", "display_text": "超猛攻擊！"}'
        )
        mock_npc.return_value = "廢物"

        with TestClient(app) as client:
            token, match_id = _setup_player_and_match(client, "ws_attacker")
            with client.websocket_connect(
                f"/ws/battle/{match_id}/ws_attacker?token={token}"
            ) as ws:
                ws.receive_text()  # consume the system join message
                ws.send_text(json.dumps({"text": "你好遜"}))
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "attack"
                assert msg["damage"] == 20
