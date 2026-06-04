from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session
from src.backend.models import Player
from src.backend.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(db: AsyncSession = Depends(get_session)) -> LeaderboardResponse:
    result = await db.execute(
        select(Player).order_by(desc(Player.total_damage)).limit(50)
    )
    players = result.scalars().all()
    entries = [
        LeaderboardEntry(
            rank=i + 1,
            username=p.username,
            total_damage=p.total_damage,
            wins=p.wins,
            losses=p.losses,
        )
        for i, p in enumerate(players)
    ]
    return LeaderboardResponse(entries=entries)
