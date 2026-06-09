"""REST API routes for match management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session
from src.backend.models import Match, MatchStatus, Player, GameRound
from src.backend.schemas.match import CreateMatchRequest, MatchResponse, PlayerMatchmakingResponse, MatchHistoryEntry
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

        # Reject if the opponent is offline
        from src.backend.api.ws.battle_ws import online_players, active_connections_count
        opponent_id_str = str(opponent.id)
        is_online = (opponent_id_str in online_players) or (req.opponent in active_connections_count and active_connections_count[req.opponent] > 0)
        if not is_online:
            raise HTTPException(status_code=400, detail="對手目前不在線，無法發起挑戰")

        player2_id = opponent.id

    match = Match(
        player1_id=uuid.UUID(current["sub"]),
        player2_id=player2_id,
        status=MatchStatus.pending,
    )
    db.add(match)
    await db.commit()

    match_id = str(match.id)

    # Notify the opponent via their lobby WebSocket
    if not is_npc and player2_id and opponent_id_str in online_players:
        import json
        opponent_ws_info = online_players[opponent_id_str]
        opponent_ws = opponent_ws_info["websocket"]
        
        # Check if the opponent is searching in the queue
        if opponent_ws_info.get("is_searching"):
            # Auto-accept the match, stop searching, and redirect both to the battle arena
            opponent_ws_info["is_searching"] = False
            try:
                await opponent_ws.send_text(json.dumps({
                    "type": "match_found",
                    "match_id": match_id,
                    "opponent": current["username"]
                }, ensure_ascii=False))
            except Exception as e:
                print(f"[WS ERROR] Failed to send match_found to opponent: {e}", flush=True)
        else:
            # Send challenge request to opponent
            try:
                await opponent_ws.send_text(json.dumps({
                    "type": "match_challenge",
                    "match_id": match_id,
                    "challenger": current["username"]
                }, ensure_ascii=False))
            except Exception as e:
                print(f"[WS ERROR] Failed to send match_challenge to opponent: {e}", flush=True)

    return MatchResponse(
        match_id=match_id,
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


@router.get("/history", response_model=list[MatchHistoryEntry])
async def list_match_history(
    db: AsyncSession = Depends(get_session),
    current: dict = Depends(get_current_player),
) -> list[MatchHistoryEntry]:
    """Get a list of all finished matches in the system for public history."""
    result = await db.execute(
        select(Match)
        .where(Match.status == MatchStatus.finished)
        .order_by(Match.ended_at.desc())
    )
    matches = result.scalars().all()

    history = []
    for m in matches:
        # Get player1 username
        p1_res = await db.execute(select(Player.username).where(Player.id == m.player1_id))
        p1_name = p1_res.scalar_one_or_none() or "Unknown"

        # Get player2 username
        p2_name = "NPC"
        if m.player2_id:
            p2_res = await db.execute(select(Player.username).where(Player.id == m.player2_id))
            p2_name = p2_res.scalar_one_or_none() or "Unknown"

        # Get winner username
        winner_name = None
        if m.winner_id:
            w_res = await db.execute(select(Player.username).where(Player.id == m.winner_id))
            winner_name = w_res.scalar_one_or_none()

        # Get rounds statistics
        r_count_res = await db.execute(
            select(GameRound).where(GameRound.match_id == m.id)
        )
        rounds = r_count_res.scalars().all()
        r_count = len(rounds)
        total_dmg = sum(r.damage for r in rounds)

        # Timestamp
        ts = m.ended_at.timestamp() if m.ended_at else 0.0

        history.append(
            MatchHistoryEntry(
                match_id=str(m.id),
                player1_username=p1_name,
                player2_username=p2_name,
                winner_username=winner_name,
                round_count=r_count,
                total_damage=total_dmg,
                timestamp=ts,
            )
        )

    return history


