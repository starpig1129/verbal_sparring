"""REST API routes for match management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session
from src.backend.models import Match, MatchStatus, Player
from src.backend.schemas.match import CreateMatchRequest, MatchResponse, PlayerMatchmakingResponse
from src.backend.services.auth import get_current_player

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.post("", response_model=MatchResponse, status_code=201)
async def create_match(
    req: CreateMatchRequest,
    db: AsyncSession = Depends(get_session),
    current: dict = Depends(get_current_player),
) -> MatchResponse:
    """Create a new match against an NPC or a registered human opponent.

    Args:
        req: The request body containing the ``opponent`` field.
        db: Injected async database session.
        current: Decoded JWT payload from the ``Authorization`` header,
            containing ``sub`` (player UUID as string) and ``username``.

    Returns:
        A ``MatchResponse`` with the new match's ID, the opponent value, and
        whether the opponent is an NPC.

    Raises:
        HTTPException: 404 if a human opponent username is not found in the
            database.
    """
    is_npc = req.opponent.lower() == "npc"
    player2_id: uuid.UUID | None = None

    if not is_npc:
        result = await db.execute(select(Player).where(Player.username == req.opponent))
        opponent = result.scalar_one_or_none()
        if not opponent:
            raise HTTPException(status_code=404, detail="Opponent not found")
        if str(opponent.id) == current["sub"]:
            raise HTTPException(status_code=400, detail="Cannot create a match against yourself")
        player2_id = opponent.id

    match = Match(
        player1_id=uuid.UUID(current["sub"]),
        player2_id=player2_id,
        status=MatchStatus.pending,
    )
    db.add(match)
    await db.commit()

    return MatchResponse(
        match_id=str(match.id),
        opponent=req.opponent,
        is_npc=is_npc,
    )


@router.get("/players", response_model=list[PlayerMatchmakingResponse])
async def list_other_players(
    db: AsyncSession = Depends(get_session),
    current: dict = Depends(get_current_player),
) -> list[PlayerMatchmakingResponse]:
    """Get a list of all other players in the system for matchmaking."""
    from src.backend.api.ws.battle_ws import active_connections_count

    current_uuid = uuid.UUID(current["sub"])
    result = await db.execute(
        select(Player).where(Player.id != current_uuid).order_by(Player.username)
    )
    players = result.scalars().all()

    return [
        PlayerMatchmakingResponse(
            id=str(p.id),
            username=p.username,
            wins=p.wins,
            losses=p.losses,
            total_damage=p.total_damage,
            is_online=p.username in active_connections_count and active_connections_count[p.username] > 0,
        )
        for p in players
    ]

