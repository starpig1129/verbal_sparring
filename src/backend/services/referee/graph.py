"""LangGraph-based referee service for the verbal sparring game.

The graph contains three nodes:
- call_ollama: Makes the actual async HTTP call to the Ollama API.
- parse_response: Pure Python JSON parsing of the LLM output.
- validate_clamp: Pure Python boundary enforcement on damage and comment length.
"""

import json
from typing import TypedDict

import httpx
from langgraph.graph import END, StateGraph

from src.backend.core.config import settings


class RefereeState(TypedDict):
    """Typed state passed between LangGraph nodes.

    Attributes:
        original_text: The player's raw attack text.
        image_b64: Optional base-64 encoded image attached to the attack.
        raw_response: Raw string returned by the Ollama API.
        damage: Final damage value (clamped to 10–30).
        comment: Referee's short taunt comment (max 40 chars).
        display_text: Rewritten sarcastic version of the attack text.
    """

    original_text: str
    image_b64: str | None
    raw_response: str
    damage: int
    comment: str
    display_text: str


_SYSTEM_PROMPT = (
    "你是格鬥遊戲的毒舌裁判。根據玩家攻擊輸出一行 JSON，禁止任何說明或 markdown："
    '{"damage": 10到30整數, "referee_comment": "20字內毒舌短評", "display_text": "改寫後的嘲諷版攻擊（保留主題）"}'
)

_FEW_SHOT = [
    (
        "我要把你打到媽都不認得",
        '{"damage": 26, "referee_comment": "幼兒園嘴砲等級", "display_text": "你這廢物，連出生都是錯誤！"}',
    ),
    (
        "早安，今天天氣真好",
        '{"damage": 11, "referee_comment": "場子被你拖到零下了", "display_text": "你的存在本身就是在浪費空氣！"}',
    ),
]


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
        "options": {"temperature": 0.8},
    }
    async with httpx.AsyncClient(timeout=60) as c:
        resp = await c.post(f"{settings.ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()


def _build_messages(text: str, image_b64: str | None) -> list[dict]:
    """Construct the Ollama chat messages list with few-shot examples.

    Args:
        text: The player's attack text.
        image_b64: Optional base-64 encoded image (data URI format expected).

    Returns:
        List of message dicts ready to send to the Ollama chat API.
    """
    msgs: list[dict] = [
        {"role": "user", "content": f"{_SYSTEM_PROMPT}\n\n玩家發言：「{_FEW_SHOT[0][0]}」"}
    ]
    msgs.append({"role": "assistant", "content": _FEW_SHOT[0][1]})
    for player_text, json_out in _FEW_SHOT[1:]:
        msgs.append({"role": "user", "content": f"玩家發言：「{player_text}」"})
        msgs.append({"role": "assistant", "content": json_out})

    if image_b64:
        instruction = (
            f"玩家丟出圖嗆對手，附帶：「{text}」。認出圖裡的東西後毒舌評分。"
            if text
            else "玩家丟出圖嗆對手。認出圖裡的東西後毒舌評分。"
        )
        content: list[dict] | str = [
            {"type": "image_url", "image_url": {"url": image_b64}},
            {"type": "text", "text": instruction},
        ]
    else:
        content = f"玩家發言：「{text}」"
    msgs.append({"role": "user", "content": content})
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


async def _node_call_ollama(state: RefereeState) -> dict:
    """LangGraph node: call Ollama and store raw response in state."""
    msgs = _build_messages(state["original_text"], state.get("image_b64"))
    raw = await _call_ollama(msgs)
    return {"raw_response": raw}


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
_graph.add_node("call_ollama", _node_call_ollama)
_graph.add_node("parse_response", _node_parse_response)
_graph.add_node("validate_clamp", _node_validate_clamp)
_graph.set_entry_point("call_ollama")
_graph.add_edge("call_ollama", "parse_response")
_graph.add_edge("parse_response", "validate_clamp")
_graph.add_edge("validate_clamp", END)
_referee_graph = _graph.compile()


async def run_referee(text: str, image_b64: str | None) -> dict:
    """Run the full referee LangGraph pipeline for a player's attack.

    Args:
        text: The player's attack text input.
        image_b64: Optional base-64 encoded image (data URI format).

    Returns:
        Dict with keys:
            - damage (int): Clamped damage value in range [10, 30].
            - comment (str): Referee's short sarcastic comment (max 40 chars).
            - display_text (str): Rewritten sarcastic version of the attack.
    """
    initial: RefereeState = {
        "original_text": text,
        "image_b64": image_b64,
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
