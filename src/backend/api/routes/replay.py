import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session
from src.backend.models import GameRound, Match, Player
from src.backend.schemas.replay import ReplayResponse, RoundSnapshot

router = APIRouter(prefix="/api/replay", tags=["replay"])


@router.get("/{match_id}", response_model=ReplayResponse)
async def get_replay(
    match_id: str, db: AsyncSession = Depends(get_session)
) -> ReplayResponse:
    try:
        mid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid match_id")

    match_result = await db.execute(select(Match).where(Match.id == mid))
    if not match_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Match not found")

    rounds_result = await db.execute(
        select(GameRound)
        .where(GameRound.match_id == mid)
        .order_by(GameRound.round_number)
    )
    rounds = rounds_result.scalars().all()

    snapshots: list[RoundSnapshot] = []
    for r in rounds:
        attacker_name: str | None = "NPC"
        if r.attacker_id:
            p_result = await db.execute(
                select(Player).where(Player.id == r.attacker_id)
            )
            player = p_result.scalar_one_or_none()
            attacker_name = player.username if player else "Unknown"
        snapshots.append(
            RoundSnapshot(
                round_number=r.round_number,
                attacker=attacker_name,
                original_text=r.original_text,
                display_text=r.display_text,
                damage=r.damage,
                referee_comment=r.referee_comment,
                hp_snapshot=r.hp_snapshot,
            )
        )

    return ReplayResponse(match_id=match_id, rounds=snapshots)
