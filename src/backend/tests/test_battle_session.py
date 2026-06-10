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


async def test_round_survives_llm_outage(db):
    """When the LLM backend is unreachable, the round completes on fallbacks."""

    async def _raise(_msgs):
        raise ConnectionError("vllm down")

    dead_llm = AsyncMock()
    dead_llm.ainvoke.side_effect = _raise

    with patch("src.backend.services.game.battle_session._referee_llm", dead_llm), \
         patch("src.backend.services.game.battle_session._npc_llm", dead_llm):
        session = BattleSession(
            match_id="m-outage",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 100},
        )
        outputs = {
            name: out
            async for name, out in session.process_attack_streaming("嗆聲", "p1", db)
        }

    assert 10 <= outputs["score_player_attack"]["damage"] <= 30
    assert outputs["npc_generate"]["npc_text"]  # fallback taunt, not empty
    assert 10 <= outputs["npc_score"]["npc_damage"] <= 30
    assert outputs["npc_score"]["game_over"] is False


def test_apply_damage_bonuses():
    """Crit at 28+, combo keeps building at 20+, low rolls reset the streak."""
    from src.backend.services.game.battle_session import apply_damage_bonuses

    # Low base: no bonuses, streak resets
    assert apply_damage_bonuses(15, 3) == (15, False, 0)
    # First high hit: streak starts, no combo bonus yet, crit applies
    assert apply_damage_bonuses(30, 0) == (35, True, 1)
    # Third consecutive high hit: +4 combo, +5 crit
    assert apply_damage_bonuses(30, 2) == (39, True, 3)
    # Combo bonus caps at +6; 20 is not a crit
    assert apply_damage_bonuses(20, 5) == (26, False, 6)


async def test_combo_builds_across_turns(db):
    """Consecutive high-damage attacks accumulate combo bonus damage."""
    mock_ref = _delayed_llm(
        '{"damage": 30, "referee_comment": "猛", "display_text": "重擊"}', 0.01
    )
    mock_npc = _delayed_llm("不痛不癢", 0.01)

    with patch("src.backend.services.game.battle_session._referee_llm", mock_ref), \
         patch("src.backend.services.game.battle_session._npc_llm", mock_npc):
        session = BattleSession(
            match_id="m-combo",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 100},
        )
        first = {
            name: out
            async for name, out in session.process_attack_streaming("第一擊", "p1", db)
        }
        second = {
            name: out
            async for name, out in session.process_attack_streaming("第二擊", "p1", db)
        }

    # Turn 1: base 30 → crit +5, streak 1 (no combo bonus yet)
    assert first["score_player_attack"]["damage"] == 35
    assert first["score_player_attack"]["is_crit"] is True
    assert first["score_player_attack"]["combo_count"] == 1
    # Turn 2: base 30 → crit +5 and combo +2 at streak 2
    assert second["score_player_attack"]["damage"] == 37
    assert second["score_player_attack"]["combo_count"] == 2
    # NPC builds its own independent streak
    assert second["npc_score"]["npc_combo_count"] == 2
