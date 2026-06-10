"""Persistent per-match LangGraph battle session.

One BattleSession per active match.  A MemorySaver checkpointer keeps
BattleState alive across multiple process_attack() calls, so:
  - The NPC sees the full conversation as proper HumanMessage / AIMessage turns.
  - The referee receives the recent battle turns as labelled context.
  - No state is rebuilt from scratch on each round.

Call destroy_session(match_id) when the match ends to free the checkpointer.
"""

import logging
import asyncio
import json
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config import (
    MEMORY_ANALYSIS_PROMPT,
    NPC_SYSTEM_PROMPT,
    REFEREE_FEW_SHOTS,
    REFEREE_SYSTEM_PROMPT,
    make_chat_llm,
    settings,
)
from src.backend.services.npc.agent import _get_memory, fallback_taunt
from src.backend.services.referee.graph import _extract_json, fallback_referee_result

logger = logging.getLogger(__name__)

# ── Module-level LLM instances (shared across all sessions) ───────────────────

_referee_llm = make_chat_llm("referee", settings.referee_temperature)
_npc_llm = make_chat_llm("player", settings.player_temperature)


# ── State ─────────────────────────────────────────────────────────────────────

class BattleState(TypedDict):
    # Battle dialogue as proper LangChain turns; add_messages appends on each invocation.
    # NPC mode  : HumanMessage(player_text) / AIMessage(npc_text)
    # PvP mode  : HumanMessage("[SenderName] text") for both players
    messages: Annotated[list[BaseMessage], add_messages]

    # Persistent game state (survives across invocations via MemorySaver)
    hp: dict[str, int]
    current_turn: str
    round_number: int
    is_npc_match: bool
    player_id: str          # URL-param room key for the human player (used in hp dict)
    player_uuid: str        # JWT sub UUID — used for DB / NpcMemory lookups
    npc_memory: dict        # NpcMemory snapshot, fetched before each turn so
                            # npc_generate never touches the DB while running
                            # in parallel with the WS loop's persistence.

    # Per-invocation inputs (overwritten each call)
    attack_text: str
    attack_image: str | None
    attacker_id: str        # UUID string of the attacker

    # Referee output for the human's attack
    damage: int
    ref_comment: str
    ref_display_text: str

    # NPC turn output (NPC matches only)
    npc_text: str
    npc_damage: int
    npc_ref_comment: str
    npc_ref_display_text: str

    game_over: bool
    winner: str | None      # UUID string or "NPC"


# ── Referee helpers ───────────────────────────────────────────────────────────

def _build_referee_messages(
    attack_text: str,
    attacker_display: str,
    hp_attacker: int,
    hp_defender: int,
    round_number: int,
    recent_messages: list[BaseMessage],
    image_b64: str | None = None,
) -> list:
    """Build referee message list.

    Structure:
      SystemMessage        — referee instructions
      HumanMessage/AI x N — few-shot examples
      HumanMessage         — battle context + recent dialogue + attack to score
    """
    msgs: list = [SystemMessage(content=REFEREE_SYSTEM_PROMPT)]
    # Few-shots use same format as real attack messages — use directly
    for inp, out in REFEREE_FEW_SHOTS:
        msgs.append(HumanMessage(content=inp))
        msgs.append(AIMessage(content=out))

    situation = (
        f"[Round {round_number} | {attacker_display} HP: {hp_attacker} "
        f"| Opponent HP: {hp_defender}]"
    )

    # Append recent battle dialogue as labelled context inside one HumanMessage
    context_parts = [situation]
    if recent_messages:
        context_parts.append("[Recent dialogue]:")
        for msg in recent_messages[-4:]:
            if isinstance(msg, HumanMessage):
                raw = msg.content if isinstance(msg.content, str) else "（圖片）"
                context_parts.append(f"  Player: 「{raw}」")
            elif isinstance(msg, AIMessage):
                raw = msg.content if isinstance(msg.content, str) else "（NPC 出手）"
                context_parts.append(f"  NPC: 「{raw}」")

    if image_b64:
        instruction = (
            f"玩家丟出圖嗆對手，附帶：「{attack_text}」。認出圖裡的東西後毒舌評分。"
            if attack_text
            else "玩家丟出圖嗆對手。認出圖裡的東西後毒舌評分。"
        )
        context_parts.append(instruction)
        msgs.append(
            HumanMessage(
                content=[
                    {"type": "image_url", "image_url": {"url": image_b64}},
                    {"type": "text", "text": "\n".join(context_parts)},
                ]
            )
        )
    else:
        context_parts.append(f"Score this attack: 「{attack_text}」")
        msgs.append(HumanMessage(content="\n".join(context_parts)))

    return msgs


async def _score(
    attack_text: str,
    attacker_display: str,
    hp_attacker: int,
    hp_defender: int,
    round_number: int,
    recent_messages: list[BaseMessage],
    image_b64: str | None = None,
) -> dict:
    """Invoke the referee LLM and return parsed damage / comment / display_text."""
    msgs = _build_referee_messages(
        attack_text, attacker_display, hp_attacker, hp_defender,
        round_number, recent_messages, image_b64,
    )
    try:
        response = await _referee_llm.ainvoke(msgs)
    except Exception as e:
        # A transient LLM outage must degrade the verdict, not abort the round.
        logger.error(f"[REFEREE ERROR] LLM call failed: {e}. Using fallback.")
        return fallback_referee_result(attack_text)
    parsed = _extract_json(response.content)
    if parsed is None:
        return {"damage": 15, "comment": "裁判嘴瓢了", "display_text": attack_text or "（無言以對）"}
    return {
        "damage": max(10, min(30, int(parsed.get("damage", 15)))),
        "comment": str(parsed.get("referee_comment", "裁判已介入"))[:40],
        "display_text": str(parsed.get("display_text", attack_text or "")),
    }


# ── NPC helper ────────────────────────────────────────────────────────────────

async def _generate_npc_attack(state: BattleState) -> str:
    """Generate NPC attack using the full battle conversation as proper turns.

    The NPC LLM sees:
      SystemMessage — role + current battle state
      HumanMessage  — player's first attack
      AIMessage     — NPC's response
      ...  (full battle history)
      HumanMessage  — player's latest attack  ← generates response here
    """
    player_id = state["player_id"]
    npc_hp = state["hp"].get("NPC", 100)
    player_hp = state["hp"].get(player_id, 100)

    memory = state.get("npc_memory") or {}
    memory_hint = ""
    if memory.get("round_count", 0) > 0:
        patterns = ", ".join(memory.get("attack_patterns", [])[:3])
        weaknesses = ", ".join(memory.get("weaknesses", [])[:3])
        if patterns:
            memory_hint += f"\n[Known patterns]: {patterns}"
        if weaknesses:
            memory_hint += f"\n[Exploitable weaknesses]: {weaknesses}"

    system_content = (
        f"{NPC_SYSTEM_PROMPT}\n\n"
        f"[Round {state['round_number']} | NPC HP: {npc_hp} | Opponent HP: {player_hp}]"
        f"{memory_hint}"
    )

    # Cap the history sent to the LLM: the opening turns anchor the battle's
    # tone, the recent turns carry the thread. Unbounded growth slows every
    # round and risks pushing the system prompt out of the context window.
    history = list(state["messages"])
    if len(history) > 14:
        history = history[:2] + history[-12:]

    npc_msgs: list = [SystemMessage(content=system_content)]
    npc_msgs.extend(history)

    try:
        response = await _npc_llm.ainvoke(npc_msgs)
        npc_text = response.content.strip()
        if not npc_text:
            raise ValueError("Empty response from NPC LLM")
        return npc_text
    except Exception as e:
        # A transient LLM outage must degrade the taunt, not abort the turn.
        logger.error(f"[NPC ERROR] LLM call failed: {e}. Using fallback taunt.")
        return fallback_taunt()


# ── Graph nodes ───────────────────────────────────────────────────────────────

async def _node_score_player_attack(
    state: BattleState, config: RunnableConfig
) -> dict:
    """Score the current player's attack and update HP."""
    is_npc = state["is_npc_match"]
    attacker_id = state["attacker_id"]
    target_key = "NPC" if is_npc else next(
        (k for k in state["hp"] if k != attacker_id), attacker_id
    )

    round_num = state["round_number"] + 1
    # Exclude the message we just appended (last entry) from "recent" context
    recent = list(state["messages"][:-1])[-4:]

    scored = await _score(
        state["attack_text"], attacker_id,
        state["hp"].get(attacker_id, 100), state["hp"].get(target_key, 100),
        round_num, recent, state.get("attack_image"),
    )

    new_hp = dict(state["hp"])
    new_hp[target_key] = max(0, new_hp.get(target_key, 100) - scored["damage"])
    game_over = new_hp[target_key] <= 0

    # NPC fields are NOT reset here: npc_generate may run in the same
    # parallel superstep and write npc_text — two writers to one plain key
    # would raise InvalidUpdateError. Resets happen in _build_turn_input.
    return {
        "hp": new_hp,
        "round_number": round_num,
        "damage": scored["damage"],
        "ref_comment": scored["comment"],
        "ref_display_text": scored["display_text"],
        "game_over": game_over,
        "winner": attacker_id if game_over else None,
        "current_turn": target_key if not game_over else state["current_turn"],
    }


async def _node_npc_generate(
    state: BattleState, config: RunnableConfig
) -> dict:
    """Generate NPC counter-attack text and add it to conversation history.

    Runs in parallel with score_player_attack, so it must not touch the DB —
    opponent memory is pre-fetched into state.npc_memory.
    """
    npc_text = await _generate_npc_attack(state)
    return {
        "messages": [AIMessage(content=npc_text)],  # add_messages appends
        "npc_text": npc_text,
    }


async def _node_npc_score(
    state: BattleState, config: RunnableConfig
) -> dict | None:
    """Score the NPC's attack (already in state.npc_text), apply damage."""
    if state["game_over"]:
        # The player's attack already ended the match while npc_generate was
        # running in parallel — discard the NPC turn entirely (None = no state
        # write; an empty dict would raise InvalidUpdateError).
        return None

    player_id = state["player_id"]
    npc_text = state["npc_text"]
    npc_hp = state["hp"].get("NPC", 100)
    player_hp = state["hp"].get(player_id, 100)
    round_num = state["round_number"] + 1

    # Exclude the NPC message we just appended (last entry) from referee context
    recent = list(state["messages"][:-1])[-4:]

    scored = await _score(npc_text, "NPC", npc_hp, player_hp, round_num, recent)

    new_hp = dict(state["hp"])
    new_hp[player_id] = max(0, player_hp - scored["damage"])
    game_over = new_hp[player_id] <= 0

    return {
        "hp": new_hp,
        "round_number": round_num,
        "npc_damage": scored["damage"],
        "npc_ref_comment": scored["comment"],
        "npc_ref_display_text": scored["display_text"],
        "game_over": game_over,
        "winner": "NPC" if game_over else None,
        "current_turn": player_id if not game_over else state["current_turn"],
    }


def _route_entry(state: BattleState) -> list[str]:
    """Fan out at the start of each turn.

    NPC matches run referee scoring and NPC generation in parallel — the NPC
    only needs the player's words (already in messages), not the referee's
    verdict, so the two LLM calls need not be sequential.
    """
    if state["is_npc_match"]:
        return ["score_player_attack", "npc_generate"]
    return ["score_player_attack"]


# ── Graph ─────────────────────────────────────────────────────────────────────

def _compile_graph(checkpointer: MemorySaver):
    g = StateGraph(BattleState)
    g.add_node("score_player_attack", _node_score_player_attack)
    g.add_node("npc_generate", _node_npc_generate)
    g.add_node("npc_score", _node_npc_score)
    g.add_conditional_edges(
        START, _route_entry, ["score_player_attack", "npc_generate"]
    )
    # Join: npc_score waits for both parallel branches. In PvP matches
    # npc_generate never runs, so the join never fires and the graph ends
    # after score_player_attack.
    g.add_edge(["score_player_attack", "npc_generate"], "npc_score")
    g.add_edge("npc_score", END)
    return g.compile(checkpointer=checkpointer)


# ── Post-match memory analysis ────────────────────────────────────────────────

# Keep strong references to fire-and-forget tasks so they are not GC'd mid-run.
_background_tasks: set[asyncio.Task] = set()


def spawn_background_task(coro) -> asyncio.Task:
    """Run a coroutine as a tracked fire-and-forget task.

    Holds a strong reference until completion and logs any exception instead
    of letting it vanish silently.
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        _background_tasks.discard(t)
        if not t.cancelled() and t.exception():
            logger.error(f"[BG TASK ERROR] {t.exception()!r}")

    task.add_done_callback(_on_done)
    return task


async def analyze_and_update_player_memory(
    player_id: str,
    messages: list[BaseMessage],
    total_damage_dealt_to_npc: int,
    total_rounds: int,
) -> None:
    """Analyse the completed battle and update NpcMemory with comprehensive intel.

    Called as a background task after match_over; extracts attack_patterns and
    weaknesses from the full dialogue via LLM, then persists to NpcMemory.
    Opens its own DB session — the caller's WS-scoped session may already be
    closed by the time this runs.

    Args:
        player_id: UUID string of the human player.
        messages: Full battle messages list from BattleState.
        total_damage_dealt_to_npc: Total damage the player dealt to the NPC.
        total_rounds: Number of rounds played.
    """
    if not messages:
        return

    # Extract only HumanMessages (player's attacks) for the analysis
    player_attacks = [
        m.content for m in messages
        if isinstance(m, HumanMessage) and isinstance(m.content, str)
    ]
    if not player_attacks:
        return

    battle_summary = "\n".join(f"- 「{t}」" for t in player_attacks)
    avg_dmg_per_round = total_damage_dealt_to_npc / total_rounds if total_rounds > 0 else 0

    analysis_msgs = [
        SystemMessage(content=MEMORY_ANALYSIS_PROMPT),
        HumanMessage(
            content=(
                f"Battle: {total_rounds} rounds, player dealt avg {avg_dmg_per_round:.1f} HP/round.\n"
                f"Player attacks:\n{battle_summary}"
            )
        ),
    ]

    try:
        response = await _npc_llm.ainvoke(analysis_msgs)
        parsed = _extract_json(response.content)
        if not parsed:
            return

        new_patterns = [str(p)[:20] for p in parsed.get("attack_patterns", [])[:4]]
        new_weaknesses = [str(w)[:20] for w in parsed.get("weaknesses", [])[:4]]

        from sqlalchemy import select
        from src.backend.core.database import SessionFactory
        from src.backend.models import NpcMemory
        import uuid as _uuid

        async with SessionFactory() as db:
            result = await db.execute(
                select(NpcMemory).where(NpcMemory.opponent_id == _uuid.UUID(player_id))
            )
            mem = result.scalar_one_or_none()
            if not mem:
                mem = NpcMemory(opponent_id=_uuid.UUID(player_id))
                db.add(mem)

            # Merge new patterns/weaknesses (keep at most 10 unique entries each)
            existing_patterns = set(mem.attack_patterns)
            existing_weaknesses = set(mem.weaknesses)
            mem.attack_patterns = list(existing_patterns | set(new_patterns))[-10:]
            mem.weaknesses = list(existing_weaknesses | set(new_weaknesses))[-10:]

            # Update running average damage
            total = mem.avg_damage_recv * mem.round_count + total_damage_dealt_to_npc
            mem.round_count += total_rounds
            mem.avg_damage_recv = total / mem.round_count if mem.round_count > 0 else 0.0

            await db.commit()
        logger.info(f"[MEMORY] Updated NPC memory for player {player_id}: "
              f"patterns={new_patterns}, weaknesses={new_weaknesses}")
    except Exception as e:
        logger.error(f"[MEMORY ERROR] Failed to analyse player memory: {e}")


# ── BattleSession ─────────────────────────────────────────────────────────────

class BattleSession:
    """Persistent LangGraph session for one active match.

    The MemorySaver checkpointer keeps BattleState alive between
    process_attack() calls.  Call destroy() when the match ends.
    """

    def __init__(
        self,
        match_id: str,
        player_id: str,
        player_uuid: str,
        is_npc: bool,
        initial_hp: dict[str, int],
        initial_messages: list = None,
    ) -> None:
        self._checkpointer = MemorySaver()
        self._graph = _compile_graph(self._checkpointer)
        self._match_id = match_id
        self._thread_id = match_id
        self._initialized = False
        self._last_messages: list[BaseMessage] = list(initial_messages) if initial_messages else []
        self._initial_state: BattleState = {
            "messages": initial_messages or [],
            "hp": dict(initial_hp),
            "current_turn": player_id,
            "round_number": 0,
            "is_npc_match": is_npc,
            "player_id": player_id,
            "player_uuid": player_uuid,
            "npc_memory": {},
            "attack_text": "",
            "attack_image": None,
            "attacker_id": player_id,
            "damage": 0,
            "ref_comment": "",
            "ref_display_text": "",
            "npc_text": "",
            "npc_damage": 0,
            "npc_ref_comment": "",
            "npc_ref_display_text": "",
            "game_over": False,
            "winner": None,
        }

    async def process_attack_streaming(
        self,
        attack_text: str,
        attacker_id: str,
        db: AsyncSession,
        image_b64: str | None = None,
        sender_display: str | None = None,
    ):
        """Yield (node_name, node_output) as each graph node completes.

        Callers can broadcast results immediately after each yield rather than
        waiting for the entire graph (scorer + NPC turn) to finish.

        Yields:
            ("score_player_attack", node_output_dict)
            ("npc_generate", node_output_dict)  # NPC words, before scoring
            ("npc_score",    node_output_dict)  # damage + referee comment
        """
        config: RunnableConfig = {"configurable": {"thread_id": self._thread_id}}
        turn_input = self._build_turn_input(attack_text, attacker_id, image_b64, sender_display)
        if self._initial_state["is_npc_match"]:
            # Pre-fetch opponent memory sequentially: npc_generate runs in
            # parallel with the caller's DB writes and must not share the session.
            turn_input["npc_memory"] = await _get_memory(
                db, self._initial_state["player_uuid"]
            )

        async for chunk in self._graph.astream(turn_input, config=config, stream_mode="updates"):
            node_name = next(iter(chunk))
            node_output = chunk[node_name]
            yield (node_name, node_output)

        # Sync _last_messages from checkpoint so get_messages() is accurate
        try:
            snapshot = self._graph.get_state({"configurable": {"thread_id": self._thread_id}})
            if snapshot and snapshot.values:
                self._last_messages = list(snapshot.values.get("messages", []))
        except Exception:
            pass

    def _build_turn_input(
        self,
        attack_text: str,
        attacker_id: str,
        image_b64: str | None,
        sender_display: str | None,
    ) -> dict:
        """Build the input dict for a graph invocation and mark as initialized."""
        is_npc = self._initial_state["is_npc_match"]
        label = sender_display or attacker_id
        msg_content = (
            attack_text or "（圖片）"
            if is_npc
            else f"[{label}] {attack_text or '（圖片）'}"
        )
        turn_input: dict = {
            "messages": [HumanMessage(content=msg_content)],
            "attack_text": attack_text,
            "attack_image": image_b64,
            "attacker_id": attacker_id,
            # Per-turn resets, applied as input before the superstep so the
            # parallel branches never double-write the same key.
            "npc_text": "",
            "npc_damage": 0,
            "npc_ref_comment": "",
            "npc_ref_display_text": "",
            "game_over": False,
            "winner": None,
        }
        if not self._initialized:
            turn_input = {**self._initial_state, **turn_input}
            self._initialized = True
        return turn_input

    async def process_attack(
        self,
        attack_text: str,
        attacker_id: str,
        db: AsyncSession,
        image_b64: str | None = None,
        sender_display: str | None = None,
    ) -> BattleState:
        """Process one player's attack and return the final BattleState."""
        config: RunnableConfig = {"configurable": {"thread_id": self._thread_id}}
        turn_input = self._build_turn_input(attack_text, attacker_id, image_b64, sender_display)
        if self._initial_state["is_npc_match"]:
            turn_input["npc_memory"] = await _get_memory(
                db, self._initial_state["player_uuid"]
            )
        result = await self._graph.ainvoke(turn_input, config=config)
        self._last_messages = list(result.get("messages", []))
        return result

    def get_messages(self) -> list[BaseMessage]:
        """Return accumulated battle messages from the last process_attack result."""
        return list(self._last_messages)

    def destroy(self) -> None:
        """Release the checkpointer and compiled graph."""
        del self._checkpointer
        del self._graph


# ── Registry ──────────────────────────────────────────────────────────────────

_sessions: dict[str, BattleSession] = {}


def create_battle_session(
    match_id: str,
    player_id: str,
    player_uuid: str,
    is_npc: bool,
    initial_hp: dict[str, int],
    initial_messages: list = None,
) -> BattleSession:
    session = BattleSession(match_id, player_id, player_uuid, is_npc, initial_hp, initial_messages)
    _sessions[match_id] = session
    return session


def get_battle_session(match_id: str) -> BattleSession | None:
    return _sessions.get(match_id)


def destroy_battle_session(match_id: str) -> None:
    session = _sessions.pop(match_id, None)
    if session:
        session.destroy()
