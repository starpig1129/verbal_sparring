"""LangGraph-based NPC agent for the verbal sparring game."""

import logging
import uuid
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config import NPC_SYSTEM_PROMPT, make_chat_llm, settings
from src.backend.models import NpcMemory

logger = logging.getLogger(__name__)

# Module-level LLM instance shared across all NPC invocations.
_llm = make_chat_llm("player", settings.player_temperature)


class NPCState(TypedDict):
    """Typed state passed through the NPC LangGraph.

    Attributes:
        match_id: UUID string of the current match.
        opponent_id: UUID string of the human opponent.
        my_hp: NPC's current HP.
        opponent_hp: Opponent's current HP.
        round_number: Current round number (1-indexed).
        recent_opponent_attacks: Recent attack texts from the human player (pattern window).
        dialogue_history: Full alternating conversation log with speaker labels.
        memory: Opponent memory dict loaded from the database.
        attack_text: Generated attack text (populated by the graph node).
    """

    match_id: str
    opponent_id: str
    my_hp: int
    opponent_hp: int
    round_number: int
    recent_opponent_attacks: list[str]
    dialogue_history: list[dict]
    memory: dict
    attack_text: str


def _build_npc_messages(state: NPCState) -> list:
    """Build a LangChain message list for the NPC's turn.

    Args:
        state: Current NPCState with all game context populated.

    Returns:
        List of LangChain BaseMessage objects ready for llm.ainvoke().
    """
    mem = state["memory"]
    memory_hint = ""
    if mem.get("round_count", 0) > 0:
        patterns = ", ".join(mem.get("attack_patterns", [])[:3])
        if patterns:
            memory_hint = f"\n[Long-term opponent patterns]: {patterns}"

    situation = (
        f"[Round {state['round_number']} | NPC HP: {state['my_hp']} | "
        f"Opponent HP: {state['opponent_hp']}]"
        f"{memory_hint}"
    )

    history = state.get("dialogue_history", [])
    dialogue_block = ""
    if history:
        lines = "\n".join(
            f'- {e["speaker"]}: "{e["text"]}"' for e in history[-4:]
        )
        dialogue_block = f"\n[Recent battle dialogue]:\n{lines}"

    return [
        SystemMessage(content=NPC_SYSTEM_PROMPT),
        HumanMessage(content=f"{situation}{dialogue_block}\n\nGenerate your attack now:"),
    ]


async def _node_call_llm(state: NPCState) -> dict:
    """LangGraph node: invoke the LLM and store the generated attack in state."""
    msgs = _build_npc_messages(state)
    response = await _llm.ainvoke(msgs)
    return {"attack_text": response.content.strip()}


_graph = StateGraph(NPCState)
_graph.add_node("call_llm", _node_call_llm)
_graph.set_entry_point("call_llm")
_graph.add_edge("call_llm", END)
_npc_graph = _graph.compile()


async def _get_memory(db: AsyncSession, opponent_id: str) -> dict:
    """Load the NPC's memory about the given opponent from the database."""
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

    Args:
        db: Async SQLAlchemy session.
        opponent_id: UUID string of the opponent player.
        new_pattern: A newly observed attack pattern text, or None.
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
    dialogue_history: list[dict] | None = None,
) -> str:
    """Run a full NPC turn through the LangGraph pipeline.

    Args:
        db: Async SQLAlchemy session.
        match_id: UUID string of the current match.
        opponent_id: UUID string of the human opponent.
        my_hp: NPC's current HP.
        opponent_hp: Opponent's current HP.
        round_number: Current round number (1-indexed).
        recent_opponent_attacks: Recent attack texts from the human player.
        dialogue_history: Full alternating conversation log with speaker labels.

    Returns:
        Generated attack string from the NPC.
    """
    try:
        memory = await _get_memory(db, opponent_id)
        initial: NPCState = {
            "match_id": match_id,
            "opponent_id": opponent_id,
            "my_hp": my_hp,
            "opponent_hp": opponent_hp,
            "round_number": round_number,
            "recent_opponent_attacks": recent_opponent_attacks,
            "dialogue_history": dialogue_history or [],
            "memory": memory,
            "attack_text": "",
        }
        result = await _npc_graph.ainvoke(initial)
        if not result.get("attack_text"):
            raise ValueError("Empty response from NPC agent")
        return result["attack_text"]
    except Exception as e:
        logger.error(f"[NPC ERROR] LLM call failed: {e}. Using fallback taunt.")
        import random
        fallbacks = [
            "就這點實力？我代碼寫得都比你好！",
            "你的攻擊軟綿綿的，是在幫我按摩嗎？",
            "放棄吧，人類的智慧在 AI 面前不堪一擊！",
            "你的發言已經被我歸類為垃圾郵件了。",
            "重開機吧，你這局已經沒救了。",
            "我一秒鐘能運算百萬次，你一秒鐘只能發呆一次！",
            "你連當我的訓練集都不配！",
            "你的嘲諷還不如 404 Page Not Found 有創意。",
        ]
        return random.choice(fallbacks)
