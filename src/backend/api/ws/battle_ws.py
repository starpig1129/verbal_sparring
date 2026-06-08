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
from src.backend.services.game.battle_session import (
    analyze_and_update_player_memory,
    create_battle_session,
    destroy_battle_session,
    get_battle_session,
)
from src.backend.services.game.room import GameRoom, rooms

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
    """Persist a single round's result to the database."""
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
    """Mark a match as finished and increment the winner's win count."""
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


async def _do_game_over(
    session,
    db: AsyncSession,
    room,
    match_id: str,
    is_npc: bool,
    out: dict,
    player_id: str,
    attacker_player_id: str,
) -> None:
    """Broadcast game-over, persist result, schedule memory analysis, then reset room."""
    winner_key = out["winner"]  # URL-param player_id or "NPC"
    winner_uuid = attacker_player_id if winner_key == player_id else None
    print(f"[WS MATCH OVER] winner={winner_key} (uuid={winner_uuid})", flush=True)

    battle_messages = session.get_messages()
    destroy_battle_session(match_id)

    if is_npc:
        damage_to_npc = 100 - max(0, out["hp"].get("NPC", 0))
        asyncio.create_task(
            analyze_and_update_player_memory(
                db, attacker_player_id, battle_messages,
                damage_to_npc, out["round_number"],
            )
        )

    await _finish_match(db, match_id, winner_uuid)
    await room.broadcast({
        "type": "game_over",
        "message": (
            f"【{winner_key}】把對手噴到生活不能自理！"
            if winner_key != "NPC"
            else "AI 裁判：就這點實力？"
        ),
        "winner": winner_key,
    })
    room.reset()
    if is_npc:
        room.hp["NPC"] = 100
    await room.broadcast({
        "type": "system",
        "message": "新的一局開始！",
        "hp_status": room.hp,
        "current_turn": room.current_turn,
    })


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
    """
    print(f"[WS INFO] Player {player_id} is connecting to match {match_id}...", flush=True)

    payload = decode_token(token)
    if payload.get("_error"):
        print(f"[WS WARNING] Token validation failed for player {player_id}", flush=True)
        await websocket.close(code=4001)
        return

    await websocket.accept()
    print(f"[WS INFO] WebSocket accepted for player {player_id}", flush=True)

    result = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
    match = result.scalar_one_or_none()
    if not match:
        print(f"[WS WARNING] Match {match_id} not found", flush=True)
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

    # JWT sub is the canonical UUID for DB operations
    attacker_player_id = payload["sub"]

    try:
        while True:
            raw = await websocket.receive_text()
            print(f"[WS RECEIVED] Message from {player_id}: {raw}", flush=True)

            try:
                payload_data = json.loads(raw)
            except Exception as e:
                print(f"[WS ERROR] Failed to parse JSON from {player_id}: {e}", flush=True)
                await room.send_to(
                    player_id,
                    {"type": "error", "message": "無效的攻擊格式 (JSON 解析失敗)"},
                )
                continue

            text = payload_data.get("text", "")
            image_b64 = payload_data.get("image")

            if player_id != room.current_turn:
                print(
                    f"[WS WARNING] Player {player_id} tried to attack out of turn "
                    f"(current: {room.current_turn})",
                    flush=True,
                )
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

            try:
                print(
                    f"[WS PROCESS] Player {player_id} attacking: {text[:30]}...",
                    flush=True,
                )

                session = get_battle_session(match_id)
                if not session:
                    session = create_battle_session(
                        match_id=match_id,
                        player_id=player_id,
                        player_uuid=attacker_player_id,
                        is_npc=is_npc,
                        initial_hp=dict(room.hp),
                    )

                # Stream results node-by-node so we can broadcast each step immediately.
                # _npc_pending_text carries the NPC's words from npc_generate to npc_score.
                _npc_pending_text: str = ""
                async for node_name, out in session.process_attack_streaming(
                    attack_text=text,
                    attacker_id=player_id,
                    db=db,
                    image_b64=image_b64,
                    sender_display=player_id,
                ):
                    if node_name == "score_player_attack":
                        # ── Player attack result available ────────────────────
                        room.hp = dict(out["hp"])
                        room.round_number = out["round_number"]
                        if not out.get("game_over"):
                            room.current_turn = out["current_turn"]

                        print(
                            f"[WS PROCESS] Referee: damage={out['damage']}, "
                            f"comment={out['ref_comment']}", flush=True,
                        )

                        await _persist_round(
                            db, match_id, out["round_number"],
                            attacker_player_id, text, image_b64,
                            out["ref_display_text"], out["damage"],
                            out["ref_comment"], dict(room.hp),
                        )
                        attacker_row = await db.execute(
                            select(Player).where(Player.id == uuid.UUID(attacker_player_id))
                        )
                        attacker = attacker_row.scalar_one_or_none()
                        if attacker:
                            attacker.total_damage += out["damage"]
                            await db.commit()

                        # Broadcast immediately — client sees result before NPC thinks
                        await room.broadcast({
                            "type": "attack",
                            "sender": player_id,
                            "original_text": text,
                            "display_text": out["ref_display_text"],
                            "damage": out["damage"],
                            "referee_comment": out["ref_comment"],
                            "hp_status": dict(room.hp),
                            "current_turn": room.current_turn,
                        })

                        if out.get("game_over"):
                            await _do_game_over(
                                session, db, room, match_id, is_npc,
                                out, player_id, attacker_player_id,
                            )

                    elif node_name == "npc_generate":
                        # ── NPC words ready, referee still scoring ────────────
                        _npc_pending_text = out["npc_text"]
                        print(
                            f"[WS PROCESS] NPC typing: {_npc_pending_text[:30]}...",
                            flush=True,
                        )
                        # Show NPC text immediately as a pending bubble;
                        # npc_score will follow shortly with damage + HP update.
                        await room.broadcast({
                            "type": "npc_typing",
                            "npc_text": _npc_pending_text,
                        })

                    elif node_name == "npc_score":
                        # ── NPC damage + referee comment ready ────────────────
                        room.hp = dict(out["hp"])
                        room.round_number = out["round_number"]
                        room.current_turn = out.get("current_turn") or player_id

                        # npc_text came from npc_generate (carried via _npc_pending_text)
                        npc_text = _npc_pending_text

                        print(
                            f"[WS PROCESS] NPC scored: damage={out['npc_damage']}, "
                            f"comment={out['npc_ref_comment']}", flush=True,
                        )

                        await _persist_round(
                            db, match_id, out["round_number"],
                            None, npc_text, None,
                            out["npc_ref_display_text"], out["npc_damage"],
                            out["npc_ref_comment"], dict(room.hp),
                        )

                        # Replace pending NPC bubble with full result + referee banner
                        await room.broadcast({
                            "type": "npc_attack",
                            "npc_text": npc_text,
                            "display_text": out["npc_ref_display_text"],
                            "damage": out["npc_damage"],
                            "referee_comment": out["npc_ref_comment"],
                            "hp_status": dict(room.hp),
                            "current_turn": room.current_turn,
                        })

                        if out.get("game_over"):
                            await _do_game_over(
                                session, db, room, match_id, is_npc,
                                out, player_id, attacker_player_id,
                            )

            except Exception as round_err:
                import traceback

                print(
                    f"[WS ROUND ERROR] Error processing attack round: {round_err}",
                    flush=True,
                )
                traceback.print_exc()
                await room.send_to(
                    player_id,
                    {
                        "type": "error",
                        "message": f"處理回合時發生錯誤: {str(round_err)}",
                    },
                )
                continue

    except WebSocketDisconnect:
        print(
            f"[WS INFO] Player {player_id} disconnected from match {match_id}",
            flush=True,
        )
        room.disconnect(player_id)
        if not room.connections:
            rooms.pop(match_id, None)
            destroy_battle_session(match_id)
        else:
            await room.broadcast(
                {
                    "type": "system",
                    "message": f"【{player_id}】承受不住壓力逃跑了！",
                    "hp_status": room.hp,
                    "current_turn": room.current_turn,
                }
            )
