# referee_core.py
"""
裁判推論引擎。改為呼叫本地 vLLM 的 OpenAI 相容 API（gemma-4-E4B-it AWQ/compressed-tensors INT8）。
不再在 process 內載模型 —— 模型由 vLLM serve 常駐，這裡只當 HTTP client。
"""
import json
import requests

VLLM_URL = "http://localhost:8001/v1/chat/completions"
MODEL_NAME = "gemma4-referee"

print(f"🚀 裁判引擎改接 vLLM API：{VLLM_URL}（模型 {MODEL_NAME}）")

_SYSTEM_BLOCK = (
    "你是一個格鬥遊戲的毒舌裁判，只負責「評估」玩家這回合攻擊的攻擊力。"
    "攻擊可能是一句話，也可能是一張用來嗆對手的圖。"
    "看到圖時，先認出圖裡最明顯的東西（顏色、形狀、物件、表情或文字），再針對那個具體內容毒舌，不准只敷衍說「這張圖」。"
    "你不負責跟玩家對話、不續寫劇情。"
    "輸出格式只能是一行 JSON，禁止任何前後說明、思考過程或 markdown："
    '{"damage": 10到30之間的整數, "referee_comment": "20字內的毒舌短評"}'
)

_FEW_SHOT = [
    ("我要把你打到媽都不認得", '{"damage": 26, "referee_comment": "嘴炮等級：幼兒園畢業典禮"}'),
    ("早安，今天天氣真好", '{"damage": 11, "referee_comment": "問候？場子被你拖到零下了"}'),
    ("你長得像被卡車輾過的便當", '{"damage": 24, "referee_comment": "畫面有了，扣分扣得理所當然"}'),
]


def _build_messages(original_text: str, image_data_url=None):
    """組 OpenAI 相容 messages。純文字 few-shot 教 JSON 格式；最後一則視有無圖組裝。"""
    messages = [
        {"role": "user", "content": f"{_SYSTEM_BLOCK}\n\n玩家發言：「{_FEW_SHOT[0][0]}」"},
        {"role": "assistant", "content": _FEW_SHOT[0][1]},
    ]
    for player_text, json_out in _FEW_SHOT[1:]:
        messages.append({"role": "user", "content": f"玩家發言：「{player_text}」"})
        messages.append({"role": "assistant", "content": json_out})

    if image_data_url:
        if original_text:
            instruction = f"玩家丟出這張圖嗆對手，並附帶文字：「{original_text}」。先認出圖裡的東西，再針對它與文字一起毒舌評分。"
        else:
            instruction = "玩家丟出這張圖嗆對手（沒附文字）。先認出圖裡的東西，再針對它毒舌評分。"
        final_content = [
            {"type": "image_url", "image_url": {"url": image_data_url}},
            {"type": "text", "text": instruction},
        ]
    else:
        final_content = f"玩家發言：「{original_text}」"
    messages.append({"role": "user", "content": final_content})
    return messages


def ai_referee_engine(original_text: str, image_data_url=None):
    """
    把玩家這回合攻擊（文字，或圖 + 選填文字）丟給 vLLM 當裁判評分，
    回傳 (damage, referee_comment)。image_data_url 為 data URL 字串或 None。
    """
    messages = _build_messages(original_text, image_data_url)
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 80,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(VLLM_URL, json=payload, timeout=60)
        resp.raise_for_status()
        response_text = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ vLLM 請求失敗：{e}")
        return (10, "裁判連線出包了，先扣你 10 滴血意思一下")

    parsed = _extract_json(response_text)
    if parsed is not None:
        damage_raw = parsed.get("damage", 15)
        try:
            damage = int(damage_raw)
        except (TypeError, ValueError):
            damage = 15
        damage = max(1, min(50, damage))
        return (damage, str(parsed.get("referee_comment", "裁判已無情地介入。")))

    print(f"⚠️ 解析失敗，模型原始輸出：{response_text!r}")
    snippet = response_text[:60].replace("\n", " ").strip() or "(空輸出)"
    return (10, f"裁判嘴瓢了：「{snippet}」")


def _extract_json(text: str):
    """
    從可能夾雜廢話 / markdown / 多段內容的回應裡抽出第一個合法 JSON object。
    1. 直接 json.loads  2. 去掉 ```json fence  3. 括號配對找閉合的 {...}
    """
    cleaned = text.strip()
    for candidate in (cleaned, cleaned.replace("```json", "").replace("```", "").strip()):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    depth = 0
    start = -1
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start != -1:
                candidate = cleaned[start:i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    pass
                start = -1
    return None
