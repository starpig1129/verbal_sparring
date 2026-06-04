"""WebSocket endpoint for the real-time battle arena."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session
from src.backend.models import GameRound, Match, MatchStatus, Player
from src.backend.services.auth import decode_token
from src.backend.services.game.room import GameRoom, rooms
from src.backend.services.npc.agent import run_npc_turn, update_npc_memory
from src.backend.services.referee.graph import run_referee

router = APIRouter()


async def _persist_round(
    db: AsyncSession,
    match_id: str,
    round_number: int,
    attacker_id: str | None,
    original_text: str,
    image_b64: str | None,
    display_text: str,
    damage: int,
    referee_comment: str,
    hp_snapshot: dict,
) -> None:
    """Persist a single round's result to the database.

    Args:
        db: Async SQLAlchemy session.
        match_id: UUID string of the owning match.
        round_number: Sequential round counter within the match.
        attacker_id: UUID string of the attacking player, or None for NPC.
        original_text: The raw text the attacker submitted.
        image_b64: Optional base-64 image attached to the attack.
        display_text: Referee-rewritten sarcastic version of the attack.
        damage: Clamped damage value (10–30).
        referee_comment: Short sarcastic comment from the referee.
        hp_snapshot: Dict mapping player_id to HP after this round.
    """
    rnd = GameRound(
        match_id=uuid.UUID(match_id),
        round_number=round_number,
        attacker_id=uuid.UUID(attacker_id) if attacker_id else None,
        original_text=original_text,
        image_b64=image_b64,
        display_text=display_text,
        damage=damage,
        referee_comment=referee_comment,
        hp_snapshot=hp_snapshot,
    )
    db.add(rnd)
    await db.commit()


async def _finish_match(
    db: AsyncSession, match_id: str, winner_id: str | None
) -> None:
    """Mark a match as finished and increment the winner's win count.

    Args:
        db: Async SQLAlchemy session.
        match_id: UUID string of the match to finalise.
        winner_id: UUID string of the winning player, or None if the NPC won.
    """
    result = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
    match = result.scalar_one_or_none()
    if match:
        match.status = MatchStatus.finished
        match.winner_id = uuid.UUID(winner_id) if winner_id else None
        match.ended_at = datetime.now(timezone.utc)
        await db.commit()

    if winner_id:
        result = await db.execute(
            select(Player).where(Player.id == uuid.UUID(winner_id))
        )
        winner = result.scalar_one_or_none()
        if winner:
            winner.wins += 1
            await db.commit()


@router.websocket("/ws/battle/{match_id}/{player_id}")
async def battle_ws(
    websocket: WebSocket,
    match_id: str,
    player_id: str,
    token: str = "",
    db: AsyncSession = Depends(get_session),
) -> None:
    """WebSocket endpoint that drives the full battle lifecycle.

    Authentication is performed via the ``token`` query parameter.  On
    success the connection is accepted and the player joins (or creates) the
    in-memory ``GameRoom`` for the given ``match_id``.

    Message protocol (client → server):
        ``{"text": "<attack>", "image": "<optional base-64>"}``

    Broadcast message types (server → all clients):
        - ``system``: Informational messages (join/leave/new round).
        - ``attack``: Result of a human player's attack.
        - ``npc_attack``: Result of an NPC auto-attack.
        - ``game_over``: Match concluded; includes the winner.
        - ``turn_error``: Sent only to the player who attacked out of turn.

    Args:
        websocket: The incoming WebSocket connection.
        match_id: UUID string of the target match (path parameter).
        player_id: Display identifier used within the room (path parameter).
        token: JWT access token passed as a query parameter.
        db: Injected async database session.
    """
    payload = decode_token(token)
    if payload.get("_error"):
        await websocket.close(code=4001)
        return

    await websocket.accept()

    result = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
    match = result.scalar_one_or_none()
    if not match:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Match not found"})
        )
        await websocket.close()
        return

    is_npc = match.player2_id is None
    if match_id not in rooms:
        rooms[match_id] = GameRoom(match_id=match_id, is_npc=is_npc)

    room = rooms[match_id]
    room.connect(player_id, websocket)

    if is_npc and "NPC" not in room.hp:
        room.hp["NPC"] = 100

    if not room.current_turn:
        room.current_turn = player_id

    if match.status == MatchStatus.pending and (is_npc or room.is_full()):
        match.status = MatchStatus.ongoing
        match.started_at = datetime.now(timezone.utc)
        await db.commit()

    await room.broadcast(
        {
            "type": "system",
            "message": f"【{player_id}】進入競技場！",
            "hp_status": room.hp,
            "current_turn": room.current_turn,
        }
    )

    attacker_player_id = payload["sub"]

    try:
        while True:
            raw = await websocket.receive_text()
            payload_data = json.loads(raw)
            text = payload_data.get("text", "")
            image_b64 = payload_data.get("image")

            if player_id != room.current_turn:
                await room.send_to(
                    player_id,
                    {
                        "type": "turn_error",
                        "message": "還沒輪到你！",
                        "hp_status": room.hp,
                        "current_turn": room.current_turn,
                    },
                )
                continue

            if not text and not image_b64:
                continue

            room.round_number += 1
            room.record_attack(text or "（圖片）")

            ref = await run_referee(text, image_b64)
            damage = ref["damage"]
            comment = ref["comment"]
            display_text = ref["display_text"]

            if is_npc:
                target = "NPC"
            else:
                other = [p for p in room.hp if p != player_id]
                target = other[0] if other else player_id

            room.hp[target] = max(0, room.hp[target] - damage)

            await _persist_round(
                db,
                match_id,
                room.round_number,
                attacker_player_id,
                text,
                image_b64,
                display_text,
                damage,
                comment,
                dict(room.hp),
            )

            attacker_result = await db.execute(
                select(Player).where(Player.id == uuid.UUID(attacker_player_id))
            )
            attacker = attacker_result.scalar_one_or_none()
            if attacker:
                attacker.total_damage += damage
                await db.commit()

            room.current_turn = target
            await room.broadcast(
                {
                    "type": "attack",
                    "sender": player_id,
                    "display_text": display_text,
                    "damage": damage,
                    "referee_comment": comment,
                    "hp_status": dict(room.hp),
                    "current_turn": room.current_turn,
                }
            )

            if room.hp[target] <= 0:
                await _finish_match(db, match_id, attacker_player_id)
                await room.broadcast(
                    {
                        "type": "game_over",
                        "message": f"【{player_id}】把對手噴到生活不能自理！",
                        "winner": player_id,
                    }
                )
                room.reset()
                if is_npc and "NPC" not in room.hp:
                    room.hp["NPC"] = 100
                await room.broadcast(
                    {
                        "type": "system",
                        "message": "新的一局開始！",
                        "hp_status": room.hp,
                        "current_turn": room.current_turn,
                    }
                )
                continue

            if is_npc and room.current_turn == "NPC":
                npc_text = await run_npc_turn(
                    db=db,
                    match_id=match_id,
                    opponent_id=attacker_player_id,
                    my_hp=room.hp.get("NPC", 100),
                    opponent_hp=room.hp.get(player_id, 100),
                    round_number=room.round_number,
                    recent_opponent_attacks=room.recent_attacks,
                )
                npc_ref = await run_referee(npc_text, None)
                room.hp[player_id] = max(0, room.hp.get(player_id, 100) - npc_ref["damage"])
                room.round_number += 1

                await _persist_round(
                    db,
                    match_id,
                    room.round_number,
                    None,
                    npc_text,
                    None,
                    npc_ref["display_text"],
                    npc_ref["damage"],
                    npc_ref["comment"],
                    dict(room.hp),
                )

                room.current_turn = player_id
                await room.broadcast(
                    {
                        "type": "npc_attack",
                        "display_text": npc_ref["display_text"],
                        "damage": npc_ref["damage"],
                        "referee_comment": npc_ref["comment"],
                        "hp_status": dict(room.hp),
                    }
                )

                if room.hp.get(player_id, 100) <= 0:
                    try:
                        asyncio.create_task(
                            update_npc_memory(
                                db,
                                attacker_player_id,
                                room.recent_attacks[-1] if room.recent_attacks else None,
                                npc_ref["damage"],
                            )
                        )
                    except RuntimeError:
                        pass
                    await _finish_match(db, match_id, None)
                    await room.broadcast(
                        {
                            "type": "game_over",
                            "message": "AI 裁判：就這點實力？",
                            "winner": "NPC",
                        }
                    )
                    room.reset()
                    if "NPC" not in room.hp:
                        room.hp["NPC"] = 100

    except WebSocketDisconnect:
        room.disconnect(player_id)
        if not room.connections:
            rooms.pop(match_id, None)
        else:
            await room.broadcast(
                {
                    "type": "system",
                    "message": f"【{player_id}】承受不住壓力逃跑了！",
                    "hp_status": room.hp,
                    "current_turn": room.current_turn,
                }
            )
