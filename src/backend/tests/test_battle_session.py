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

    # Base fallback verdict is 10–30; a 28+ roll crits for +5 (max 35)
    assert 10 <= outputs["score_player_attack"]["damage"] <= 35
    assert outputs["npc_generate"]["npc_text"]  # fallback taunt, not empty
    assert 10 <= outputs["npc_score"]["npc_damage"] <= 35
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


def test_style_for_round_rotation():
    """Persona holds for 6 rounds, then rotates; offset shifts the start."""
    from src.backend.services.game import battle_session as bs

    styles = [{"name": "A", "directive": "a"}, {"name": "B", "directive": "b"}]
    with patch.object(bs, "REFEREE_STYLES", styles):
        assert bs.style_for_round(0, 1)["name"] == "A"
        assert bs.style_for_round(0, 6)["name"] == "A"
        assert bs.style_for_round(0, 7)["name"] == "B"
        assert bs.style_for_round(0, 13)["name"] == "A"  # wraps around
        assert bs.style_for_round(1, 1)["name"] == "B"   # per-match offset
    with patch.object(bs, "REFEREE_STYLES", []):
        assert bs.style_for_round(0, 1) is None


async def test_referee_prompt_includes_style(db):
    """The persona directive reaches the referee prompt and the node output."""
    from src.backend.services.game import battle_session as bs

    captured: list = []

    async def capture(msgs):
        captured.append(msgs)
        msg = MagicMock()
        msg.content = REF_JSON
        return msg

    mock_ref = AsyncMock()
    mock_ref.ainvoke.side_effect = capture
    mock_npc = _delayed_llm("回嗆", 0.01)
    styles = [{"name": "武俠說書人", "directive": "用武俠說書人口吻。"}]

    with patch.object(bs, "REFEREE_STYLES", styles), \
         patch("src.backend.services.game.battle_session._referee_llm", mock_ref), \
         patch("src.backend.services.game.battle_session._npc_llm", mock_npc):
        session = BattleSession(
            match_id="m-style",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 100},
        )
        outputs = {
            name: out
            async for name, out in session.process_attack_streaming("嗆", "p1", db)
        }

    # Persona block appears in the final context message of the referee call
    assert "武俠說書人" in captured[0][-1].content
    assert outputs["score_player_attack"]["referee_style"] == "武俠說書人"
    # Round 1 is not a rotation — the join announcement covers it
    assert outputs["score_player_attack"]["referee_style_changed"] is False


async def test_npc_prompt_includes_trained_genre(db):
    """The NPC's fighting school reaches its prompt with the trained cue format."""
    from src.backend.services.game import battle_session as bs

    captured: list = []

    async def capture(msgs):
        captured.append(msgs)
        msg = MagicMock()
        msg.content = "隔壁阿明都升官了，你呢？"
        return msg

    mock_npc = AsyncMock()
    mock_npc.ainvoke.side_effect = capture
    mock_ref = _delayed_llm(REF_JSON, 0.01)
    genre = {
        "key": "relative",
        "persona": "三姑媽",
        "name": "Holiday Relatives",
        "display": "過年親戚問候流",
        "directive": "Mock them like prying holiday relatives.",
    }

    with patch.object(bs, "NPC_GENRES", [genre]), \
         patch("src.backend.services.game.battle_session._referee_llm", mock_ref), \
         patch("src.backend.services.game.battle_session._npc_llm", mock_npc):
        session = BattleSession(
            match_id="m-genre",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 100},
        )
        assert session.npc_genre["name"] == "Holiday Relatives"
        async for _name, _out in session.process_attack_streaming("嗆", "p1", db):
            pass

    # The system message of the NPC generation call carries the exact
    # "Style: <Name>." cue the LoRA was trained on, plus the directive.
    system_msg = captured[0][0]
    assert "Style: Holiday Relatives." in system_msg.content
    assert "prying holiday relatives" in system_msg.content


async def test_npc_prompt_includes_battle_status_and_keyword_cue(db):
    """Battle status block and keyword-twist callout reach the NPC system message."""
    from src.backend.services.game import battle_session as bs

    captured: list = []

    async def capture(msgs):
        captured.append(msgs)
        msg = MagicMock()
        msg.content = "你自己看著辦"
        return msg

    mock_npc = AsyncMock()
    mock_npc.ainvoke.side_effect = capture
    mock_ref = _delayed_llm(REF_JSON, 0.01)

    with patch("src.backend.services.game.battle_session._referee_llm", mock_ref), \
         patch("src.backend.services.game.battle_session._npc_llm", mock_npc):
        session = BattleSession(
            match_id="m-status",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 100},
        )
        async for _name, _out in session.process_attack_streaming("你這個廢物", "p1", db):
            pass

    system_content = captured[0][0].content
    # HP context and situation directive present
    assert "BATTLE STATUS" in system_content
    assert "Your HP:" in system_content
    assert "Opponent HP:" in system_content
    # Explicit keyword callout with the actual attack text
    assert "Respond to this attack" in system_content
    assert "你這個廢物" in system_content


async def test_npc_prompt_memory_is_directive_when_present(db):
    """When memory exists, the prompt explicitly tells the NPC to exploit the weakness."""
    from src.backend.services.game import battle_session as bs

    captured: list = []

    async def capture(msgs):
        captured.append(msgs)
        msg = MagicMock()
        msg.content = "你就這樣"
        return msg

    mock_npc = AsyncMock()
    mock_npc.ainvoke.side_effect = capture
    mock_ref = _delayed_llm(REF_JSON, 0.01)
    fake_memory = {
        "round_count": 5,
        "attack_patterns": ["喜歡舉例"],
        "weaknesses": ["避免直接對罵"],
    }

    mock_get_memory = AsyncMock(return_value=fake_memory)
    with patch("src.backend.services.game.battle_session._referee_llm", mock_ref), \
         patch("src.backend.services.game.battle_session._npc_llm", mock_npc), \
         patch("src.backend.services.game.battle_session._get_memory", mock_get_memory):
        session = BattleSession(
            match_id="m-memory-directive",
            player_id="p1",
            player_uuid=str(uuid.uuid4()),
            is_npc=True,
            initial_hp={"p1": 100, "NPC": 100},
        )
        async for _name, _out in session.process_attack_streaming("嗆一下", "p1", db):
            pass

    system_content = captured[0][0].content
    assert "Player intel" in system_content
    assert "避免直接對罵" in system_content
    assert "exploit" in system_content.lower() or "Exploit" in system_content


def test_npc_genres_loaded_from_config():
    """All 8 trained fighting schools are available in production config."""
    from src.backend.core.config import NPC_GENRES

    assert len(NPC_GENRES) == 8
    names = {g["name"] for g in NPC_GENRES}
    assert names == {
        "Elegant Sarcasm", "Grounded Street Slang", "Friendly Banter",
        "Internet Memes", "Workplace Passive Aggressive",
        "Relationship Gaslighting", "Toxic Chicken Soup", "Holiday Relatives",
    }


def test_npc_genre_is_stable_per_match():
    """Genre is seeded by match_id: reconnects keep the same persona."""
    from src.backend.services.game.battle_session import npc_genre_for_match

    a1 = npc_genre_for_match("match-aaa")
    a2 = npc_genre_for_match("match-aaa")
    assert a1 == a2
    assert a1.get("persona")  # every genre has a persona name
    # Different matches can draw different schools (sanity: at least the
    # mapping is deterministic, not constant across all ids)
    draws = {npc_genre_for_match(f"m-{i}")["key"] for i in range(32)}
    assert len(draws) > 1
