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
        "src.backend.services.referee.graph._llm", new_callable=AsyncMock
    ) as mock_ref1, patch(
        "src.backend.services.npc.agent._llm", new_callable=AsyncMock
    ) as mock_npc1, patch(
        "src.backend.services.game.battle_session._referee_llm", new_callable=AsyncMock
    ) as mock_ref2, patch(
        "src.backend.services.game.battle_session._npc_llm", new_callable=AsyncMock
    ) as mock_npc2:
        from unittest.mock import MagicMock
        mock_ref_msg = MagicMock()
        mock_ref_msg.content = '{"damage": 15, "referee_comment": "不錯", "display_text": "你很差！"}'
        mock_ref1.ainvoke.return_value = mock_ref_msg
        mock_ref2.ainvoke.return_value = mock_ref_msg

        mock_npc_msg = MagicMock()
        mock_npc_msg.content = "你的臉跟你的攻擊一樣難看"
        mock_npc1.ainvoke.return_value = mock_npc_msg
        mock_npc2.ainvoke.return_value = mock_npc_msg

        with TestClient(app) as client:
            token, match_id = _setup_player_and_match(client, "ws_tester")
            with client.websocket_connect(
                f"/ws/battle/{match_id}/ws_tester?token={token}"
            ) as ws:
                history = json.loads(ws.receive_text())
                assert history["type"] == "history"
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "system"
                assert "ws_tester" in msg["message"]


def test_websocket_attack_reduces_hp():
    """Sending an attack message should reduce the target's HP by the referee damage."""
    app.dependency_overrides[get_session] = _ws_test_session

    with patch(
        "src.backend.services.referee.graph._llm", new_callable=AsyncMock
    ) as mock_ref1, patch(
        "src.backend.services.npc.agent._llm", new_callable=AsyncMock
    ) as mock_npc1, patch(
        "src.backend.services.game.battle_session._referee_llm", new_callable=AsyncMock
    ) as mock_ref2, patch(
        "src.backend.services.game.battle_session._npc_llm", new_callable=AsyncMock
    ) as mock_npc2:
        from unittest.mock import MagicMock
        mock_ref_msg = MagicMock()
        mock_ref_msg.content = '{"damage": 20, "referee_comment": "猛", "display_text": "超猛攻擊！"}'
        mock_ref1.ainvoke.return_value = mock_ref_msg
        mock_ref2.ainvoke.return_value = mock_ref_msg

        mock_npc_msg = MagicMock()
        mock_npc_msg.content = "廢物"
        mock_npc1.ainvoke.return_value = mock_npc_msg
        mock_npc2.ainvoke.return_value = mock_npc_msg

        with TestClient(app) as client:
            token, match_id = _setup_player_and_match(client, "ws_attacker")
            with client.websocket_connect(
                f"/ws/battle/{match_id}/ws_attacker?token={token}"
            ) as ws:
                ws.receive_text()  # consume the history message
                ws.receive_text()  # consume the system join message
                ws.send_text(json.dumps({"text": "你好遜"}))
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "player_typing"
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "attack"
                assert msg["damage"] == 20


def _recv_skipping_list_updates(ws) -> dict:
    """Receive the next message that isn't a player_list_update push."""
    while True:
        msg = json.loads(ws.receive_text())
        if msg.get("type") != "player_list_update":
            return msg


def test_matchmaking_queue():
    """Two players connecting to the queue WS should be matched together."""
    app.dependency_overrides[get_session] = _ws_test_session

    with TestClient(app) as client:
        # Register user 1
        reg1 = client.post("/api/auth/register", json={"username": "user1", "password": "pw"})
        t1 = reg1.json()["access_token"]

        # Register user 2
        reg2 = client.post("/api/auth/register", json={"username": "user2", "password": "pw"})
        t2 = reg2.json()["access_token"]

        # Connect user 1 to queue
        with client.websocket_connect(f"/ws/queue?token={t1}") as ws1:
            msg1 = _recv_skipping_list_updates(ws1)
            assert msg1["type"] == "queued"

            # Connect user 2 to queue
            with client.websocket_connect(f"/ws/queue?token={t2}") as ws2:
                # User 2 should trigger a match immediately
                msg2 = _recv_skipping_list_updates(ws2)
                assert msg2["type"] == "match_found"
                assert msg2["opponent"] == "user1"
                match_id = msg2["match_id"]
                assert match_id is not None

                # User 1 should also receive the match_found message
                msg1_match = _recv_skipping_list_updates(ws1)
                assert msg1_match["type"] == "match_found"
                assert msg1_match["opponent"] == "user2"
                assert msg1_match["match_id"] == match_id

