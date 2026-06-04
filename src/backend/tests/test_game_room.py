"""Unit tests for GameRoom — pure synchronous, no database required."""

from unittest.mock import MagicMock

from src.backend.services.game.room import GameRoom


def test_connect_sets_hp():
    room = GameRoom(match_id="test-match")
    ws = MagicMock()
    room.connect("alice", ws)
    assert room.hp["alice"] == 100


def test_is_full_npc():
    room = GameRoom(match_id="npc-match", is_npc=True)
    ws = MagicMock()
    room.connect("alice", ws)
    assert room.is_full() is True


def test_is_full_human_vs_human():
    room = GameRoom(match_id="pvp-match", is_npc=False)
    ws1, ws2 = MagicMock(), MagicMock()
    room.connect("alice", ws1)
    assert room.is_full() is False
    room.connect("bob", ws2)
    assert room.is_full() is True


def test_record_attack_keeps_last_3():
    room = GameRoom(match_id="m")
    for i in range(5):
        room.record_attack(f"attack{i}")
    assert room.recent_attacks == ["attack2", "attack3", "attack4"]


def test_reset_restores_hp():
    room = GameRoom(match_id="m")
    room.connect("alice", MagicMock())
    room.hp["alice"] = 30
    room.reset()
    assert room.hp["alice"] == 100
