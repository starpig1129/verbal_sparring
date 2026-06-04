import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models import GameRound, Match, MatchStatus, NpcMemory, Player

# Run all tests in this module under the session-scoped event loop so they
# can share the session-scoped test_engine fixture without cross-loop errors.
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_player(db: AsyncSession) -> None:
    """Player row is persisted with correct default values.

    Args:
        db: Async database session fixture.
    """
    player = Player(username="tester", password_hash="hash")
    db.add(player)
    await db.commit()
    result = await db.execute(select(Player).where(Player.username == "tester"))
    p = result.scalar_one()
    assert p.wins == 0
    assert p.total_damage == 0


async def test_create_match(db: AsyncSession) -> None:
    """Match row with no player FKs (NPC match) is persisted correctly.

    Args:
        db: Async database session fixture.
    """
    match = Match(status=MatchStatus.ongoing)
    db.add(match)
    await db.commit()
    result = await db.execute(select(Match).where(Match.status == MatchStatus.ongoing))
    m = result.scalar_one()
    assert m.player1_id is None  # NPC match


async def test_create_game_round(db: AsyncSession) -> None:
    """GameRound row is linked to a match and stores JSONB hp_snapshot correctly.

    Args:
        db: Async database session fixture.
    """
    match = Match()
    db.add(match)
    await db.flush()
    rnd = GameRound(
        match_id=match.id,
        round_number=1,
        display_text="你好遜！",
        damage=20,
        referee_comment="有點東西",
        hp_snapshot={"Player_1": 80, "Player_2": 100},
    )
    db.add(rnd)
    await db.commit()
    result = await db.execute(select(GameRound).where(GameRound.match_id == match.id))
    r = result.scalar_one()
    assert r.damage == 20
    assert r.hp_snapshot["Player_1"] == 80


async def test_create_npc_memory(db: AsyncSession) -> None:
    """NpcMemory row is created for an opponent player with default list fields.

    Args:
        db: Async database session fixture.
    """
    player = Player(username="npc_opponent", password_hash="hash2")
    db.add(player)
    await db.flush()
    mem = NpcMemory(opponent_id=player.id)
    db.add(mem)
    await db.commit()
    result = await db.execute(
        select(NpcMemory).where(NpcMemory.opponent_id == player.id)
    )
    m = result.scalar_one()
    assert m.attack_patterns == []
    assert m.weaknesses == []
    assert m.avg_damage_recv == 0.0
    assert m.round_count == 0
