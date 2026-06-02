# app.py
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from typing import Dict
import json

# 裁判引擎（vLLM HTTP client，編譯成 .so）
import referee_core

app = FastAPI(title="唇槍舌戰 API")

BATTLE_HTML = Path(__file__).parent / "battle.html"

@app.get("/")
async def serve_battle_page():
    return FileResponse(BATTLE_HTML, media_type="text/html")


class GameRoom:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.hp = {"Player_1": 100, "Player_2": 100}
        self.current_turn = "Player_1"  # 回合制：目前輪到誰出招，Player_1 先手

    def reset(self):
        self.hp = {"Player_1": 100, "Player_2": 100}
        self.current_turn = "Player_1"

    async def connect(self, player_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[player_id] = websocket

    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))

room = GameRoom()

@app.websocket("/ws/battle/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    await room.connect(player_id, websocket)
    
    await room.broadcast({
        "type": "system",
        "message": f"【{player_id}】進入了競技場！",
        "hp_status": room.hp,
        "current_turn": room.current_turn,
    })

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            original_text = payload.get("text", "")
            image_b64 = payload.get("image")  # data URL 或 None（傳圖出招）

            # 回合制：不是當前回合的玩家不能出招，擋下並只回給該玩家
            if player_id != room.current_turn:
                await websocket.send_text(json.dumps({
                    "type": "turn_error",
                    "message": "還沒輪到你！等對手出完招。",
                    "hp_status": room.hp,
                    "current_turn": room.current_turn,
                }))
                continue

            # 空出招（沒文字也沒圖）直接忽略
            if not original_text and not image_b64:
                continue

            # 重點在這裡！把資料交給 vLLM 裁判引擎（圖直接以 data URL 傳遞）
            damage, comment = referee_core.ai_referee_engine(original_text, image_b64)

            target_id = "Player_2" if player_id == "Player_1" else "Player_1"
            room.hp[target_id] -= damage
            room.hp[target_id] = max(0, room.hp[target_id])

            # 出招結算完，把回合交給對方
            room.current_turn = target_id

            await room.broadcast({
                "type": "attack",
                "sender": player_id,
                "display_text": original_text,
                "display_image": image_b64,  # 原圖回傳給雙方顯示
                "damage": damage,
                "referee_comment": comment,
                "hp_status": room.hp,
                "current_turn": room.current_turn,
            })

            if room.hp[target_id] <= 0:
                await room.broadcast({
                    "type": "game_over",
                    "message": f"遊戲結束！【{player_id}】把對手噴到生活不能自理！",
                    "hp_status": room.hp,
                    "current_turn": room.current_turn,
                })
                # 重置棋盤並開新局，由 Player_1 先攻
                room.reset()
                await room.broadcast({
                    "type": "system",
                    "message": "新的一局開始！由 Player_1 先攻。",
                    "hp_status": room.hp,
                    "current_turn": room.current_turn,
                })

    except WebSocketDisconnect:
        room.disconnect(player_id)
        await room.broadcast({
            "type": "system",
            "message": f"【{player_id}】承受不住壓力逃跑了！",
            "hp_status": room.hp,
            "current_turn": room.current_turn,
        })