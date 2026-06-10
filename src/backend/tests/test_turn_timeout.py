"""Server-side anti-stall turn timeout tests (PvP only)."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

from src.backend.api.ws.battle_ws import (
    _cancel_turn_timer,
    _schedule_turn_timeout,
    _turn_timers,
)
from src.backend.services.game.room import GameRoom, rooms


def _pvp_room(match_id: str) -> tuple[GameRoom, AsyncMock, AsyncMock]:
    room = GameRoom(match_id=match_id, is_npc=False)
    ws_a, ws_b = AsyncMock(), AsyncMock()
    room.connect("alice", ws_a)
    room.connect("bob", ws_b)
    room.current_turn = "alice"
    rooms[match_id] = room
    return room, ws_a, ws_b


async def test_turn_timeout_skips_idle_player():
    room, _ws_a, ws_b = _pvp_room("m-timeout-skip")
    try:
        _schedule_turn_timeout("m-timeout-skip", room, timeout=0.1)
        await asyncio.sleep(0.15)

        assert room.current_turn == "bob"
        sent = json.loads(ws_b.send_text.call_args_list[0].args[0])
        assert sent["type"] == "turn_timeout"
        assert "alice" in sent["message"]
        assert sent["current_turn"] == "bob"
        # The watchdog re-arms for the next player
        assert "m-timeout-skip" in _turn_timers
    finally:
        _cancel_turn_timer("m-timeout-skip")
        rooms.pop("m-timeout-skip", None)


async def test_turn_timeout_cancelled_by_attack():
    room, ws_a, ws_b = _pvp_room("m-timeout-cancel")
    try:
        _schedule_turn_timeout("m-timeout-cancel", room, timeout=0.1)
        _cancel_turn_timer("m-timeout-cancel")  # what a valid attack does
        await asyncio.sleep(0.15)

        assert room.current_turn == "alice"
        ws_a.send_text.assert_not_called()
        ws_b.send_text.assert_not_called()
    finally:
        rooms.pop("m-timeout-cancel", None)


async def test_turn_timeout_noop_for_npc_room():
    room = GameRoom(match_id="m-timeout-npc", is_npc=True)
    room.connect("alice", AsyncMock())
    room.current_turn = "alice"
    rooms["m-timeout-npc"] = room
    try:
        _schedule_turn_timeout("m-timeout-npc", room, timeout=0.05)
        assert "m-timeout-npc" not in _turn_timers
    finally:
        rooms.pop("m-timeout-npc", None)


async def test_turn_timeout_noop_when_room_not_full():
    room = GameRoom(match_id="m-timeout-half", is_npc=False)
    room.connect("alice", AsyncMock())  # opponent not connected
    room.current_turn = "alice"
    rooms["m-timeout-half"] = room
    try:
        _schedule_turn_timeout("m-timeout-half", room, timeout=0.05)
        assert "m-timeout-half" not in _turn_timers
    finally:
        rooms.pop("m-timeout-half", None)
