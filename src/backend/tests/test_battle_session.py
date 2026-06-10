"""BattleSession graph tests: parallel NPC generation and game-over handling."""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

from src.backend.services.game.battle_session import BattleSession

REF_JSON = '{"damage": 15, "referee_comment": "可以", "display_text": "重寫攻擊"}'


def _delayed_llm(content: str, delay: float) -> AsyncMock:
    msg = MagicMock()
    msg.content = content

    async def _invoke(_msgs):
        await asyncio.sleep(delay)
        return msg

    llm = AsyncMock()
    llm.ainvoke.side_effect = _invoke
    return llm


async def test_npc_generation_runs_parallel_with_scoring(db):
    """Referee scoring and NPC generation overlap instead of running serially.

    Three LLM calls at 0.3s each take >= 0.9s sequentially; with the player
    scoring and NPC generation in parallel the turn completes in ~0.6s.
    """
    mock_ref = _delayed_llm(REF_JSON, 0.3)
    mock_npc = _delayed_llm("你也就這樣了", 0.3)

    with patch("src.backend.services.game.battle_session._referee_llm", mock_ref), \
         patch("src.backend.services.game.battle_session._npc_llm", mock_npc):
        session = BattleSession(
            match_id="m-parallel",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 100},
        )
        start = time.monotonic()
        events = [
            name
            async for name, _ in session.process_attack_streaming("嗆爆你", "p1", db)
        ]
        elapsed = time.monotonic() - start

    assert "score_player_attack" in events
    assert "npc_generate" in events
    assert "npc_score" in events
    assert elapsed < 0.85, f"turn took {elapsed:.2f}s — branches did not run in parallel"


async def test_npc_turn_discarded_when_player_attack_ends_match(db):
    """When the player's hit drops NPC HP to 0, the parallel NPC turn is a no-op."""
    mock_ref = _delayed_llm(
        '{"damage": 30, "referee_comment": "致命", "display_text": "終結技"}', 0.05
    )
    mock_npc = _delayed_llm("垂死掙扎", 0.05)

    with patch("src.backend.services.game.battle_session._referee_llm", mock_ref), \
         patch("src.backend.services.game.battle_session._npc_llm", mock_npc):
        session = BattleSession(
            match_id="m-lethal",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 30},
        )
        outputs = {
            name: out
            async for name, out in session.process_attack_streaming("致命一擊", "p1", db)
        }

    assert outputs["score_player_attack"]["game_over"] is True
    assert outputs["score_player_attack"]["winner"] == "p1"
    # npc_score must not apply damage after the match has ended
    assert not outputs.get("npc_score")
