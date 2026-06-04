"""LangGraph-based NPC agent for the verbal sparring game.

The agent uses a single-node graph that calls Ollama to generate a taunt
attack based on the current game state and persisted opponent memory.
Memory is loaded from PostgreSQL before the graph runs and can be updated
after each turn via :func:`update_npc_memory`.
"""

import uuid
from typing import TypedDict

import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config import settings
from src.backend.models import NpcMemory


class NPCState(TypedDict):
    """Typed state passed through the NPC LangGraph.

    Attributes:
        match_id: UUID string of the current match.
        opponent_id: UUID string of the human opponent.
        my_hp: NPC's current HP.
        opponent_hp: Opponent's current HP.
        round_number: Current round number (1-indexed).
        recent_opponent_attacks: Recent attack texts from the opponent.
        memory: Opponent memory dict loaded from the database.
        attack_text: Generated attack text (populated by the graph node).
    """

    match_id: str
    opponent_id: str
    my_hp: int
    opponent_hp: int
    round_number: int
    recent_opponent_attacks: list[str]
    memory: dict
    attack_text: str


async def _call_ollama(messages: list[dict]) -> str:
    """Send a chat request to Ollama and return the assistant message content.

    Args:
        messages: List of chat message dicts with "role" and "content" keys.

    Returns:
        Stripped string content of the assistant's reply.

    Raises:
        httpx.HTTPStatusError: If the Ollama API returns a non-2xx response.
    """
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.9},
    }
    async with httpx.AsyncClient(timeout=60) as c:
        resp = await c.post(f"{settings.ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()


_NPC_SYSTEM = (
    "你是一個毒舌 AI 格鬥選手。根據戰況與對手記憶，生成一句 20 字內的嗆聲攻擊（繁體中文）。"
    "直接輸出攻擊文字，不加任何說明。"
)


def _build_npc_messages(state: NPCState) -> list[dict]:
    """Construct the Ollama chat messages list for the NPC's turn.

    Incorporates the opponent memory summary and recent attacks into the
    prompt so the NPC can adapt its strategy.

    Args:
        state: Current NPCState with all game context populated.

    Returns:
        List of message dicts ready to send to the Ollama chat API.
    """
    mem = state["memory"]
    memory_summary = ""
    if mem.get("round_count", 0) > 0:
        patterns = "、".join(mem.get("attack_patterns", [])[:3]) or "無特殊模式"
        weaknesses = "、".join(mem.get("weaknesses", [])[:3]) or "未知弱點"
        memory_summary = (
            f"\n對手習慣：{patterns}\n對手弱點：{weaknesses}\n歷史場數：{mem['round_count']}"
        )

    recent = "、".join(state["recent_opponent_attacks"][-3:]) or "無"
    situation = (
        f"當前戰況：我方HP {state['my_hp']} vs 對手HP {state['opponent_hp']}，"
        f"第 {state['round_number']} 回合。"
        f"對手最近攻擊：「{recent}」。"
        f"{memory_summary}"
    )
    return [
        {"role": "user", "content": f"{_NPC_SYSTEM}\n\n{situation}\n\n生成你這回合的攻擊："},
    ]


async def _node_call_ollama(state: NPCState) -> dict:
    """LangGraph node: call Ollama and store the generated attack in state.

    Args:
        state: Current NPCState with game context and opponent memory.

    Returns:
        Partial state dict containing only the ``attack_text`` key.
    """
    msgs = _build_npc_messages(state)
    text = await _call_ollama(msgs)
    return {"attack_text": text}


_graph = StateGraph(NPCState)
_graph.add_node("call_ollama", _node_call_ollama)
_graph.set_entry_point("call_ollama")
_graph.add_edge("call_ollama", END)
_npc_graph = _graph.compile()


async def _get_memory(db: AsyncSession, opponent_id: str) -> dict:
    """Load the NPC's memory about the given opponent from the database.

    Args:
        db: Async SQLAlchemy session.
        opponent_id: UUID string of the opponent player.

    Returns:
        Dict with keys ``attack_patterns``, ``weaknesses``,
        ``avg_damage_recv``, and ``round_count``.  Returns an empty dict
        when no memory record exists yet for this opponent.
    """
    result = await db.execute(
        select(NpcMemory).where(NpcMemory.opponent_id == uuid.UUID(opponent_id))
    )
    mem = result.scalar_one_or_none()
    if not mem:
        return {}
    return {
        "attack_patterns": mem.attack_patterns,
        "weaknesses": mem.weaknesses,
        "avg_damage_recv": mem.avg_damage_recv,
        "round_count": mem.round_count,
    }


async def update_npc_memory(
    db: AsyncSession,
    opponent_id: str,
    new_pattern: str | None,
    damage_received: int,
) -> None:
    """Update (or create) the NPC's memory record for the given opponent.

    Updates the running average damage received and appends a newly
    observed attack pattern (capped to the last 10 patterns).

    Args:
        db: Async SQLAlchemy session.
        opponent_id: UUID string of the opponent player.
        new_pattern: A newly observed attack pattern descriptor, or None.
        damage_received: Damage the NPC received this round.
    """
    result = await db.execute(
        select(NpcMemory).where(NpcMemory.opponent_id == uuid.UUID(opponent_id))
    )
    mem = result.scalar_one_or_none()
    if not mem:
        mem = NpcMemory(opponent_id=uuid.UUID(opponent_id))
        db.add(mem)
    if new_pattern and new_pattern not in mem.attack_patterns:
        mem.attack_patterns = [*mem.attack_patterns, new_pattern][-10:]
    total = mem.avg_damage_recv * mem.round_count + damage_received
    mem.round_count += 1
    mem.avg_damage_recv = total / mem.round_count
    await db.commit()


async def run_npc_turn(
    db: AsyncSession,
    match_id: str,
    opponent_id: str,
    my_hp: int,
    opponent_hp: int,
    round_number: int,
    recent_opponent_attacks: list[str],
) -> str:
    """Run a full NPC turn through the LangGraph pipeline.

    Loads the opponent's memory from PostgreSQL, invokes the LangGraph
    NPC agent, and returns the generated attack text.

    Args:
        db: Async SQLAlchemy session.
        match_id: UUID string of the current match.
        opponent_id: UUID string of the human opponent.
        my_hp: NPC's current HP.
        opponent_hp: Opponent's current HP.
        round_number: Current round number (1-indexed).
        recent_opponent_attacks: Recent attack texts from the opponent.

    Returns:
        Generated attack string from the NPC (up to ~20 Chinese characters).
    """
    memory = await _get_memory(db, opponent_id)
    initial: NPCState = {
        "match_id": match_id,
        "opponent_id": opponent_id,
        "my_hp": my_hp,
        "opponent_hp": opponent_hp,
        "round_number": round_number,
        "recent_opponent_attacks": recent_opponent_attacks,
        "memory": memory,
        "attack_text": "",
    }
    result = await _npc_graph.ainvoke(initial)
    return result["attack_text"]
