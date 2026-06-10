"""LangGraph-based referee service for the verbal sparring game."""

import logging
import json
from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from src.backend.core.config import (
    REFEREE_FEW_SHOTS,
    REFEREE_SYSTEM_PROMPT,
    make_chat_llm,
    settings,
)

logger = logging.getLogger(__name__)

# Module-level LLM instance shared across all referee invocations.
_llm = make_chat_llm("referee", settings.referee_temperature)

# Canned verdicts used when the referee LLM is unreachable, so a transient
# model outage degrades the round instead of aborting it.
FALLBACK_COMMENTS = [
    "力道不夠，回去多練練！",
    "這嘲諷，傷害比蚊子咬還低。",
    "裁判覺得你的詞彙量有待加強。",
    "嘴皮子挺溜，但沒什麼威力。",
    "這攻擊，簡直是在給對手刮痧！",
    "AI 裁判被你的尷尬言論震驚了。",
    "你是在說相聲還是在戰鬥？",
    "聽了想睡覺，換個新鮮的吧。",
]
FALLBACK_REWRITES = [
    "就這？連隔邊阿嬤出拳都比你重！",
    "你那點微末本領，拿來雜耍都嫌寒酸！",
    "看你說話的蠢樣，真替你的智商感到遺憾！",
    "別再浪費空氣了，你的存在就是個笑話！",
    "這就是你的全力？回家洗洗睡吧！",
    "聽你說話就像在聽噪音，能閉嘴嗎？",
    "說最狠的話，挨最毒的打，說的就是你吧！",
]


def fallback_referee_result(text: str) -> dict:
    """Deterministic referee verdict derived from the attack text."""
    h = abs(hash(text or ""))
    return {
        "damage": 10 + (h % 21),
        "comment": FALLBACK_COMMENTS[h % len(FALLBACK_COMMENTS)],
        "display_text": FALLBACK_REWRITES[(h + 1) % len(FALLBACK_REWRITES)],
    }


class RefereeState(TypedDict):
    """Typed state passed between LangGraph nodes.

    Attributes:
        original_text: The player's raw attack text.
        image_b64: Optional base-64 encoded image attached to the attack.
        context: Optional game context dict (round_number, hp, dialogue_history).
        raw_response: Raw string returned by the LLM.
        damage: Final damage value (clamped to 10–30).
        comment: Referee's short taunt comment (max 40 chars).
        display_text: Rewritten sarcastic version of the attack text.
    """

    original_text: str
    image_b64: str | None
    context: dict
    raw_response: str
    damage: int
    comment: str
    display_text: str


def _build_messages(state: RefereeState) -> list:
    """Build a LangChain message list: system prompt, few-shots, then current input.

    Uses proper SystemMessage / HumanMessage / AIMessage types so the system
    prompt is correctly separated from the conversation turns.

    Args:
        state: Current RefereeState with original_text, image_b64, and context.

    Returns:
        List of LangChain BaseMessage objects ready for llm.ainvoke().
    """
    msgs: list = [SystemMessage(content=REFEREE_SYSTEM_PROMPT)]

    for player_text, json_out in REFEREE_FEW_SHOTS:
        msgs.append(HumanMessage(content=f"玩家發言：「{player_text}」"))
        msgs.append(AIMessage(content=json_out))

    ctx = state.get("context") or {}
    situation = ""
    if ctx:
        r = ctx.get("round_number", 1)
        a_hp = ctx.get("attacker_hp", 100)
        d_hp = ctx.get("defender_hp", 100)
        attacker = ctx.get("attacker_name", "Player")
        history = ctx.get("dialogue_history", [])
        situation = f"[Round {r} | {attacker} HP: {a_hp} | Opponent HP: {d_hp}]\n"
        if history:
            lines = "\n".join(
                f'- {e["speaker"]}: "{e["text"]}"' for e in history[-4:]
            )
            situation += f"[Recent battle dialogue]:\n{lines}\n"

    text = state["original_text"]
    image_b64 = state.get("image_b64")

    if image_b64:
        instruction = (
            f"{situation}玩家丟出圖嗆對手，附帶：「{text}」。認出圖裡的東西後毒舌評分。"
            if text
            else f"{situation}玩家丟出圖嗆對手。認出圖裡的東西後毒舌評分。"
        )
        msgs.append(
            HumanMessage(
                content=[
                    {"type": "image_url", "image_url": {"url": image_b64}},
                    {"type": "text", "text": instruction},
                ]
            )
        )
    else:
        msgs.append(HumanMessage(content=f"{situation}玩家發言：「{text}」"))

    return msgs


def _extract_json(text: str) -> dict | None:
    """Extract the first valid JSON object from a string.

    Tries direct parse first, then strips markdown fences, then walks the
    string character-by-character to find a balanced brace pair.

    Args:
        text: Raw string potentially containing a JSON object.

    Returns:
        Parsed dict if a valid JSON object is found, otherwise None.
    """
    for candidate in (
        text.strip(),
        text.strip().replace("```json", "").replace("```", "").strip(),
    ):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    depth, start = 0, -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    obj = json.loads(text[start : i + 1])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    pass
                start = -1
    return None


async def _node_call_llm(state: RefereeState) -> dict:
    """LangGraph node: invoke the LLM and store the raw response in state."""
    msgs = _build_messages(state)
    response = await _llm.ainvoke(msgs)
    return {"raw_response": response.content}


def _node_parse_response(state: RefereeState) -> dict:
    """LangGraph node: parse the LLM JSON response into structured fields."""
    parsed = _extract_json(state["raw_response"])
    if parsed is None:
        return {
            "damage": 10,
            "comment": "裁判嘴瓢了",
            "display_text": state["original_text"] or "（無言以對）",
        }
    return {
        "damage": int(parsed.get("damage", 15)),
        "comment": str(parsed.get("referee_comment", "裁判已介入")),
        "display_text": str(parsed.get("display_text", state["original_text"] or "")),
    }


def _node_validate_clamp(state: RefereeState) -> dict:
    """LangGraph node: enforce damage range and comment length limits."""
    return {
        "damage": max(10, min(30, state["damage"])),
        "comment": state["comment"][:40],
    }


_graph = StateGraph(RefereeState)
_graph.add_node("call_llm", _node_call_llm)
_graph.add_node("parse_response", _node_parse_response)
_graph.add_node("validate_clamp", _node_validate_clamp)
_graph.set_entry_point("call_llm")
_graph.add_edge("call_llm", "parse_response")
_graph.add_edge("parse_response", "validate_clamp")
_graph.add_edge("validate_clamp", END)
_referee_graph = _graph.compile()


async def run_referee(text: str, image_b64: str | None, context: dict | None = None) -> dict:
    """Run the full referee LangGraph pipeline for a player's attack.

    Args:
        text: The player's attack text input.
        image_b64: Optional base-64 encoded image (data URI format).
        context: Optional game context. Keys: round_number, attacker_hp,
            defender_hp, attacker_name, dialogue_history.

    Returns:
        Dict with keys damage (int), comment (str), display_text (str).
    """
    try:
        initial: RefereeState = {
            "original_text": text,
            "image_b64": image_b64,
            "context": context or {},
            "raw_response": "",
            "damage": 10,
            "comment": "",
            "display_text": "",
        }
        result = await _referee_graph.ainvoke(initial)
        return {
            "damage": result["damage"],
            "comment": result["comment"],
            "display_text": result["display_text"],
        }
    except Exception as e:
        logger.error(f"[REFEREE ERROR] LLM call failed: {e}. Using fallback.")
        return fallback_referee_result(text)
