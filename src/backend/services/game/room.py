"""GameRoom: in-memory state management for a single match session."""

import json
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class GameRoom:
    """Holds all runtime state for one active match.

    Attributes:
        match_id: UUID string of the associated match record.
        is_npc: True when player2 is the AI opponent.
        connections: Mapping of player_id to their live WebSocket.
        hp: Mapping of player_id to current HP value.
        current_turn: player_id whose turn it is to attack next.
        round_number: How many rounds have completed so far.
        recent_attacks: Sliding window of the last three attack texts.
    """

    match_id: str
    is_npc: bool = False
    connections: dict[str, WebSocket] = field(default_factory=dict)
    hp: dict[str, int] = field(default_factory=dict)
    current_turn: str = ""
    round_number: int = 0
    recent_attacks: list[str] = field(default_factory=list)

    def connect(self, player_id: str, ws: WebSocket) -> None:
        """Register a player's WebSocket and initialise their HP if needed.

        Args:
            player_id: Unique identifier for the player.
            ws: The player's active WebSocket connection.
        """
        self.connections[player_id] = ws
        if player_id not in self.hp:
            self.hp[player_id] = 100

    def disconnect(self, player_id: str) -> None:
        """Remove a player's WebSocket connection from the room.

        Args:
            player_id: Unique identifier for the player to remove.
        """
        self.connections.pop(player_id, None)

    async def broadcast(self, message: dict) -> None:
        """Send a JSON-serialised message to every connected player.

        Args:
            message: Dict to serialise and send to all connections.
        """
        for ws in self.connections.values():
            await ws.send_text(json.dumps(message, ensure_ascii=False))

    async def send_to(self, player_id: str, message: dict) -> None:
        """Send a JSON-serialised message to a specific player.

        Args:
            player_id: Target player's identifier.
            message: Dict to serialise and send.
        """
        ws = self.connections.get(player_id)
        if ws:
            await ws.send_text(json.dumps(message, ensure_ascii=False))

    def is_full(self) -> bool:
        """Return True when the room has reached its player capacity.

        NPC rooms are full with one human connection; PvP rooms need two.

        Returns:
            True if the room cannot accept additional players.
        """
        if self.is_npc:
            return len(self.connections) >= 1
        return len(self.connections) >= 2

    def record_attack(self, text: str) -> None:
        """Append an attack text to the sliding window of recent attacks.

        Keeps only the last three entries.

        Args:
            text: Attack description or display text to record.
        """
        self.recent_attacks = [*self.recent_attacks, text][-3:]

    def reset(self) -> None:
        """Reset HP, turn order, and round counter for a new game session.

        All currently connected players are restored to 100 HP.  The first
        player (alphabetically) is assigned the opening turn.
        """
        self.hp = {p: 100 for p in self.connections}
        self.current_turn = sorted(self.connections.keys())[0] if self.connections else ""
        self.round_number = 0
        self.recent_attacks = []


rooms: dict[str, GameRoom] = {}
