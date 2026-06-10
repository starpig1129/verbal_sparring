"""WebSocket endpoint for the real-time battle arena."""

import logging
import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select, update
from sqlalchemy.orm import defer
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session
from src.backend.models import GameRound, Match, MatchStatus, Player
from src.backend.services.auth import decode_token
from src.backend.services.game.battle_session import (
    analyze_and_update_player_memory,
    create_battle_session,
    destroy_battle_session,
    get_battle_session,
    spawn_background_task,
)
from src.backend.services.game.room import GameRoom, rooms

logger = logging.getLogger(__name__)

router = APIRouter()

# Upper bound for one client message (text + base64 image). The frontend
# compresses images to ≤768px JPEG, well under this; anything bigger is
# either a raw photo or abuse.
MAX_WS_MESSAGE_CHARS = 1_000_000

# Active connections per username to track online status
active_connections_count: dict[str, int] = {}

# Online players in the lobby: player_id (str) -> {"username": str, "websocket": WebSocket, "is_searching": bool}
online_players: dict[str, dict] = {}

# Serialises the scan-and-claim step of matchmaking. Without it two players
# connecting simultaneously can each pick the other during an await and
# create two matches. (Single-process assumption, like the registries above.)
_matchmaking_lock = asyncio.Lock()


# PvP anti-stall: how long the current player may hold a turn. Keep in sync
# with the frontend countdown (BattlePage TURN_SECONDS).
TURN_TIMEOUT_SECONDS = 90

# One watchdog task per match; cancelled on attack, game over, or disconnect.
_turn_timers: dict[str, asyncio.Task] = {}


def _cancel_turn_timer(match_id: str) -> None:
    timer = _turn_timers.pop(match_id, None)
    if timer:
        timer.cancel()


def _schedule_turn_timeout(
    match_id: str, room: GameRoom, timeout: float = TURN_TIMEOUT_SECONDS
) -> None:
    """Skip the current player's turn if they idle too long (PvP only).

    NPC matches are exempt — an idle player there holds no one hostage. The
    watchdog only fires while both players are connected and the turn hasn't
    changed since it was armed.
    """
    _cancel_turn_timer(match_id)
    if room.is_npc or not room.current_turn or not room.is_full():
        return
    expected = room.current_turn

    async def _watchdog() -> None:
        try:
            await asyncio.sleep(timeout)
        except asyncio.CancelledError:
            return
        if (
            rooms.get(match_id) is not room
            or room.current_turn != expected
            or not room.is_full()
        ):
            return
        next_player = next((p for p in room.connections if p != expected), None)
        if not next_player:
            return
        room.current_turn = next_player
        logger.info(f"[WS TIMEOUT] {expected} idled too long in {match_id}; turn passes to {next_player}")
        try:
            await room.broadcast({
                "type": "turn_timeout",
                "message": f"【{expected}】猶豫太久，回合被跳過！",
                "hp_status": room.hp,
                "current_turn": room.current_turn,
            })
        finally:
            _schedule_turn_timeout(match_id, room, timeout)

    _turn_timers[match_id] = asyncio.create_task(_watchdog())


async def _notify_player_list_changed() -> None:
    """Nudge every lobby client to refresh its player list.

    Sent whenever a player comes online, goes offline, or enters/leaves a
    battle. Clients re-fetch via REST; slow polling remains as fallback.
    """
    payload = json.dumps({"type": "player_list_update"}, ensure_ascii=False)
    for info in list(online_players.values()):
        try:
            await info["websocket"].send_text(payload)
        except Exception:
            pass


async def _try_matchmake(
    db: AsyncSession, player_uuid: str, username: str, websocket: WebSocket
) -> None:
    """Pair the player with a searching opponent, or report queued.

    The opponent scan and the is_searching flag flips happen atomically under
    the matchmaking lock; the slower DB write and notifications happen after.
    """
    opponent_uuid: str | None = None
    opponent_info: dict | None = None

    async with _matchmaking_lock:
        for op_uuid, op_info in online_players.items():
            if op_uuid != player_uuid and op_info.get("is_searching"):
                opponent_uuid = op_uuid
                opponent_info = op_info
                break
        if opponent_uuid and opponent_info:
            # Claim both players inside the lock so no one else can match them.
            if player_uuid in online_players:
                online_players[player_uuid]["is_searching"] = False
            opponent_info["is_searching"] = False

    if not (opponent_uuid and opponent_info):
        await websocket.send_text(json.dumps({
            "type": "queued",
            "message": "已加入配對佇列，尋找對手中..."
        }, ensure_ascii=False))
        return

    match = Match(
        player1_id=uuid.UUID(opponent_uuid),
        player2_id=uuid.UUID(player_uuid),
        status=MatchStatus.pending,
    )
    db.add(match)
    await db.commit()
    match_id = str(match.id)

    try:
        await opponent_info["websocket"].send_text(json.dumps({
            "type": "match_found",
            "match_id": match_id,
            "opponent": username
        }, ensure_ascii=False))
    except Exception:
        pass

    await websocket.send_text(json.dumps({
        "type": "match_found",
        "match_id": match_id,
        "opponent": opponent_info["username"]
    }, ensure_ascii=False))


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
    bump_attacker_damage: bool = False,
) -> None:
    """Persist a single round's result (and attacker damage stats) in one commit."""
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
    if bump_attacker_damage and attacker_id:
        await db.execute(
            update(Player)
            .where(Player.id == uuid.UUID(attacker_id))
            .values(total_damage=Player.total_damage + damage)
        )
    await db.commit()


def _rebuild_initial_messages(history_rounds: list[dict], is_npc: bool) -> list:
    """Rebuild LangChain battle messages from plain history-round dicts.

    NPC matches map NPC turns to AIMessage and human turns to HumanMessage;
    PvP matches label every turn as a HumanMessage prefixed with the sender.
    """
    msgs: list = []
    for r in history_rounds:
        sender = r["attacker"]
        text = r["original_text"] or ""
        if is_npc:
            msgs.append(
                AIMessage(content=text) if sender == "NPC" else HumanMessage(content=text)
            )
        else:
            msgs.append(HumanMessage(content=f"[{sender}] {text}"))
    return msgs


async def _finish_match(
    db: AsyncSession, match_id: str, winner_id: str | None
) -> None:
    """Mark a match as finished and update wins/losses in a single commit."""
    result = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
    match = result.scalar_one_or_none()
    if not match:
        await db.rollback()
        return

    match.status = MatchStatus.finished
    match.winner_id = uuid.UUID(winner_id) if winner_id else None
    match.ended_at = datetime.now(timezone.utc)

    p1_id = match.player1_id
    p2_id = match.player2_id

    if winner_id:
        w_uuid = uuid.UUID(winner_id)
        await db.execute(
            update(Player).where(Player.id == w_uuid).values(wins=Player.wins + 1)
        )

        loser_uuid = None
        if p1_id == w_uuid:
            loser_uuid = p2_id
        elif p2_id == w_uuid:
            loser_uuid = p1_id

        if loser_uuid:
            await db.execute(
                update(Player)
                .where(Player.id == loser_uuid)
                .values(losses=Player.losses + 1)
            )
    elif p2_id is None:
        # NPC wins (or draw). In PvE, player1 is defeated by NPC.
        await db.execute(
            update(Player).where(Player.id == p1_id).values(losses=Player.losses + 1)
        )

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
    logger.info(f"[WS MATCH OVER] winner={winner_key} (uuid={winner_uuid})")

    _cancel_turn_timer(match_id)
    battle_messages = session.get_messages()
    destroy_battle_session(match_id)

    if is_npc:
        damage_to_npc = 100 - max(0, out["hp"].get("NPC", 0))
        spawn_background_task(
            analyze_and_update_player_memory(
                attacker_player_id, battle_messages,
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
    # The match is finished — lock the room so further attacks get turn_error.
    # A rematch creates a fresh Match via POST /api/matches; reusing this one
    # would write duplicate round_numbers into a finished match.
    room.current_turn = ""


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
    logger.info(f"[WS INFO] Player {player_id} is connecting to match {match_id}...")

    payload = decode_token(token)
    if payload.get("_error"):
        logger.warning(f"[WS WARNING] Token validation failed for player {player_id}")
        await websocket.close(code=4001)
        return

    username = payload.get("username")
    if username:
        active_connections_count[username] = active_connections_count.get(username, 0) + 1

    try:
        await websocket.accept()
        logger.info(f"[WS INFO] WebSocket accepted for player {player_id}")

        result = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
        match = result.scalar_one_or_none()
        if not match or match.status == MatchStatus.finished:
            logger.warning(f"[WS WARNING] Match {match_id} not found or already finished")
            await websocket.send_text(
                json.dumps({"type": "error", "message": "對局不存在或已結束"})
            )
            await websocket.close()
            return

        is_npc = match.player2_id is None

        # Get Player 1 and Player 2 usernames to map DB IDs to usernames
        p1_name = "Unknown"
        p2_name = "NPC"
        if match.player1_id:
            p1_res = await db.execute(select(Player).where(Player.id == match.player1_id))
            p1 = p1_res.scalar_one_or_none()
            if p1:
                p1_name = p1.username
        if match.player2_id:
            p2_res = await db.execute(select(Player).where(Player.id == match.player2_id))
            p2 = p2_res.scalar_one_or_none()
            if p2:
                p2_name = p2.username

        # Query all past rounds from DB. image_b64 is deferred: it can be
        # megabytes per row and nothing in history restoration needs it.
        rounds_result = await db.execute(
            select(GameRound)
            .options(defer(GameRound.image_b64))
            .where(GameRound.match_id == uuid.UUID(match_id))
            .order_by(GameRound.round_number.asc())
        )
        rounds = rounds_result.scalars().all()

        if match_id not in rooms:
            rooms[match_id] = GameRoom(match_id=match_id, is_npc=is_npc)
            room = rooms[match_id]
            # Restore room HP, round_number, and current_turn from latest DB round snapshot
            if rounds:
                latest_round = rounds[-1]
                room.hp = dict(latest_round.hp_snapshot)
                room.round_number = latest_round.round_number

                # Determine whose turn is next based on the last attacker
                if is_npc:
                    room.current_turn = p1_name
                else:
                    if latest_round.attacker_id == match.player1_id:
                        room.current_turn = p2_name
                    elif latest_round.attacker_id == match.player2_id:
                        room.current_turn = p1_name
                    else:
                        room.current_turn = p1_name
            else:
                if is_npc:
                    room.hp["NPC"] = 100
                    room.hp[p1_name] = 100
                else:
                    room.hp[p1_name] = 100
                    room.hp[p2_name] = 100
                room.current_turn = p1_name
                room.round_number = 0
        else:
            room = rooms[match_id]

        room.connect(player_id, websocket)
        # Entering a battle changes this player's lobby status (對戰中)
        await _notify_player_list_changed()

        if is_npc and "NPC" not in room.hp:
            room.hp["NPC"] = 100

        if not room.current_turn:
            room.current_turn = player_id

        if match.status == MatchStatus.pending and (is_npc or room.is_full()):
            match.status = MatchStatus.ongoing
            match.started_at = datetime.now(timezone.utc)
            await db.commit()

        # Send the "history" message to the client before broadcasting system join
        history_rounds = []
        for r in rounds:
            r_sender = p1_name if r.attacker_id == match.player1_id else (p2_name if r.attacker_id == match.player2_id else "NPC")
            history_rounds.append({
                "round_number": r.round_number,
                "attacker": r_sender,
                "original_text": r.original_text,
                "display_text": r.display_text,
                "damage": r.damage,
                "referee_comment": r.referee_comment,
                "hp_snapshot": r.hp_snapshot
            })

        await websocket.send_text(json.dumps({
            "type": "history",
            "rounds": history_rounds
        }, ensure_ascii=False))

        await room.broadcast(
            {
                "type": "system",
                "message": f"【{player_id}】進入競技場！",
                "hp_status": room.hp,
                "current_turn": room.current_turn,
            }
        )

        # Arm the anti-stall watchdog once a PvP room is full (no-op for NPC)
        _schedule_turn_timeout(match_id, room)

        # JWT sub is the canonical UUID for DB operations
        attacker_player_id = payload["sub"]

        # Eagerly initialize the battle session using history
        session = get_battle_session(match_id)
        if not session:
            session = create_battle_session(
                match_id=match_id,
                player_id=player_id,
                player_uuid=attacker_player_id,
                is_npc=is_npc,
                initial_hp=dict(room.hp),
                initial_messages=_rebuild_initial_messages(history_rounds, is_npc),
            )

        # Connect-phase queries are done. End the implicit read transaction so
        # this long-lived WS does not pin a pool connection while idle; all
        # in-loop DB work is commit-terminated and re-begins as needed.
        await db.rollback()

        try:
            while True:
                raw = await websocket.receive_text()

                # Heartbeat: keeps the connection alive through proxies
                # (Cloudflare drops WS connections idle for ~100 seconds).
                if raw == "ping":
                    await websocket.send_text("pong")
                    continue

                if len(raw) > MAX_WS_MESSAGE_CHARS:
                    await room.send_to(
                        player_id,
                        {"type": "error", "message": "訊息過大，圖片請壓縮後再上傳"},
                    )
                    continue

                logger.info(f"[WS RECEIVED] Message from {player_id}: {raw[:200]}")

                try:
                    payload_data = json.loads(raw)
                except Exception as e:
                    logger.error(f"[WS ERROR] Failed to parse JSON from {player_id}: {e}")
                    await room.send_to(
                        player_id,
                        {"type": "error", "message": "無效的攻擊格式 (JSON 解析失敗)"},
                    )
                    continue

                text = payload_data.get("text", "")
                image_b64 = payload_data.get("image")

                if player_id != room.current_turn:
                    logger.warning(f"[WS WARNING] Player {player_id} tried to attack out of turn "
                        f"(current: {room.current_turn})")
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

                # A valid attack is in flight — stop the anti-stall watchdog so
                # slow LLM scoring can't be mistaken for an idle player.
                _cancel_turn_timer(match_id)

                # Broadcast player typing/attack immediately so the opponent sees it in real-time
                await room.broadcast({
                    "type": "player_typing",
                    "sender": player_id,
                    "text": text
                })

                try:
                    logger.info(f"[WS PROCESS] Player {player_id} attacking: {text[:30]}...")

                    session = get_battle_session(match_id)
                    if not session:
                        session = create_battle_session(
                            match_id=match_id,
                            player_id=player_id,
                            player_uuid=attacker_player_id,
                            is_npc=is_npc,
                            initial_hp=dict(room.hp),
                            initial_messages=_rebuild_initial_messages(history_rounds, is_npc),
                        )

                    # Stream results node-by-node so we can broadcast each step
                    # immediately. score_player_attack and npc_generate run in
                    # parallel, so npc_generate may finish FIRST — its text is
                    # buffered and only broadcast after the player's attack
                    # result, preserving the "my damage, then NPC reply" order.
                    _npc_pending_text: str = ""
                    _player_scored = False
                    _round_over = False
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

                            logger.info(f"[WS PROCESS] Referee: damage={out['damage']}, "
                                f"comment={out['ref_comment']}")

                            await _persist_round(
                                db, match_id, out["round_number"],
                                attacker_player_id, text, image_b64,
                                out["ref_display_text"], out["damage"],
                                out["ref_comment"], dict(room.hp),
                                bump_attacker_damage=True,
                            )

                            # Broadcast immediately — client sees result before NPC thinks
                            await room.broadcast({
                                "type": "attack",
                                "sender": player_id,
                                "original_text": text,
                                "display_text": out["ref_display_text"],
                                "damage": out["damage"],
                                "is_crit": out.get("is_crit", False),
                                "combo": out.get("combo_count", 0),
                                "referee_comment": out["ref_comment"],
                                "hp_status": dict(room.hp),
                                "current_turn": room.current_turn,
                            })
                            _player_scored = True

                            if out.get("game_over"):
                                _round_over = True
                                await _do_game_over(
                                    session, db, room, match_id, is_npc,
                                    out, player_id, attacker_player_id,
                                )
                            elif _npc_pending_text:
                                # NPC finished before the referee — flush its
                                # buffered words now that the order is right.
                                await room.broadcast({
                                    "type": "npc_typing",
                                    "npc_text": _npc_pending_text,
                                })
                            else:
                                # PvP: the opponent's turn starts now
                                _schedule_turn_timeout(match_id, room)

                        elif node_name == "npc_generate":
                            # ── NPC words ready (referee may still be scoring) ────
                            _npc_pending_text = out["npc_text"]
                            logger.info(f"[WS PROCESS] NPC typing: {_npc_pending_text[:30]}...")
                            if _player_scored and not _round_over:
                                # Show NPC text as a pending bubble; npc_score
                                # follows shortly with damage + HP update.
                                await room.broadcast({
                                    "type": "npc_typing",
                                    "npc_text": _npc_pending_text,
                                })

                        elif node_name == "npc_score":
                            if _round_over or not out:
                                # Player's attack already ended the match — the
                                # parallel NPC turn is discarded.
                                continue

                            # ── NPC damage + referee comment ready ────────────────
                            room.hp = dict(out["hp"])
                            room.round_number = out["round_number"]
                            room.current_turn = out.get("current_turn") or player_id

                            # npc_text came from npc_generate (carried via _npc_pending_text)
                            npc_text = _npc_pending_text

                            logger.info(f"[WS PROCESS] NPC scored: damage={out['npc_damage']}, "
                                f"comment={out['npc_ref_comment']}")

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
                                "is_crit": out.get("npc_is_crit", False),
                                "combo": out.get("npc_combo_count", 0),
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

                    logger.error(f"[WS ROUND ERROR] Error processing attack round: {round_err}")
                    logger.exception("round processing failed")
                    await room.send_to(
                        player_id,
                        {
                            "type": "error",
                            "message": f"處理回合時發生錯誤: {str(round_err)}",
                        },
                    )
                    continue

        except WebSocketDisconnect:
            logger.info(f"[WS INFO] Player {player_id} disconnected from match {match_id}")
            room.disconnect(player_id)
            # Room is no longer full — don't skip turns onto a missing player.
            # Re-armed when the player reconnects (join broadcast path).
            _cancel_turn_timer(match_id)
            await _notify_player_list_changed()
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
    finally:
        if username and username in active_connections_count:
            active_connections_count[username] -= 1
            if active_connections_count[username] <= 0:
                active_connections_count.pop(username, None)


@router.websocket("/ws/queue")
async def queue_ws(
    websocket: WebSocket,
    token: str = "",
    searching: str = "true",
    db: AsyncSession = Depends(get_session),
) -> None:
    """WebSocket endpoint for matchmaking queue."""
    payload = decode_token(token)
    if payload.get("_error"):
        await websocket.close(code=4001)
        return

    username = payload.get("username")
    player_uuid = payload.get("sub")
    if not username or not player_uuid:
        await websocket.close(code=4002)
        return

    await websocket.accept()

    # Update active connections count
    active_connections_count[username] = active_connections_count.get(username, 0) + 1

    try:
        is_searching_init = searching.lower() == "true"

        online_players[player_uuid] = {
            "username": username,
            "websocket": websocket,
            "is_searching": is_searching_init
        }
        await _notify_player_list_changed()

        if is_searching_init:
            await _try_matchmake(db, player_uuid, username, websocket)

        # Keep the connection alive and listen for search/cancel/decline actions
        while True:
            raw_data = await websocket.receive_text()
            if raw_data == "ping":
                await websocket.send_text("pong")
                continue

            try:
                data = json.loads(raw_data)
            except Exception:
                continue

            msg_type = data.get("type")
            if msg_type == "start_matchmaking":
                if player_uuid in online_players:
                    online_players[player_uuid]["is_searching"] = True
                await _try_matchmake(db, player_uuid, username, websocket)

            elif msg_type == "cancel_matchmaking":
                if player_uuid in online_players:
                    online_players[player_uuid]["is_searching"] = False

            elif msg_type == "decline_challenge":
                m_id = data.get("match_id")
                if m_id:
                    result = await db.execute(select(Match).where(Match.id == uuid.UUID(m_id)))
                    m = result.scalar_one_or_none()
                    if m and m.status == MatchStatus.pending:
                        m.status = MatchStatus.finished
                        await db.commit()

                        # Notify the game room if it exists
                        from src.backend.services.game.room import rooms as game_rooms
                        if m_id in game_rooms:
                            await game_rooms[m_id].broadcast({
                                "type": "challenge_declined",
                                "message": "對手拒絕了你的挑戰"
                            })
                    else:
                        # Nothing to change — release the read transaction so
                        # the idle queue WS doesn't pin a pool connection.
                        await db.rollback()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[QUEUE ERROR] {e}")
    finally:
        # Clean up online players
        if player_uuid in online_players:
            online_players.pop(player_uuid, None)

        # Clean up active connections
        if username in active_connections_count:
            active_connections_count[username] -= 1
            if active_connections_count[username] <= 0:
                active_connections_count.pop(username, None)

        await _notify_player_list_changed()

