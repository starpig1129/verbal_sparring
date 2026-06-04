# 唇槍舌戰技術棧升級設計規格

**日期：** 2026-06-04  
**狀態：** 已核准  
**範疇：** 完整技術棧升級 — Vite React + FastAPI + PostgreSQL + Cloudflare + LangGraph + Ollama

---

## 1. 背景與目標

現有系統為單檔 FastAPI + 純 HTML，裁判引擎透過 HTTP 打本地 vLLM，無持久化、無玩家帳號、只支援單一全域房間。

本次升級目標：
- 以 Vite + React 取代純 HTML，部署至 Cloudflare Pages
- 後端加入 PostgreSQL 做完整持久化（玩家帳號、對戰紀錄、回放、NPC 記憶）
- 以 Ollama（gemma4:12b）取代 vLLM
- 以 LangGraph 重構 AI 推論層：裁判 graph + AI NPC agent
- 支援多房間對戰
- Cloudflare CDN/DNS proxy 保護後端真實 IP

---

## 2. 整體架構

```
[Cloudflare Pages]              [Cloudflare CDN/DNS proxy]
  Vite + React build   ──▶         自架 FastAPI server
  (靜態部署)                          ↓             ↓
                               PostgreSQL      Ollama (gemma4:12b)
                               (AsyncPG)        (本地常駐)
```

**請求流程：**

```
瀏覽器
  │  HTTP REST  (登入/排行榜/回放)
  │  WebSocket  ws://{domain}/ws/battle/{match_id}/{player_id}
  ▼
FastAPI
  ├─ 遊戲迴圈（HP、回合、房間） ── 記憶體
  ├─ 持久化（對戰紀錄、玩家帳號）── PostgreSQL (SQLAlchemy async)
  └─ AI 推論 ── LangGraph
       ├─ RefereeGraph  ──▶ Ollama API
       └─ NPCAgent      ──▶ Ollama API + PostgreSQL（記憶工具）
```

---

## 3. 資料夾結構

```
verbal_sparring/
├── src/
│   ├── frontend/                   # Vite + React + TypeScript
│   │   ├── src/
│   │   │   ├── components/         # BattleArena, HPBar, ChatLog, AttackInput
│   │   │   ├── hooks/              # useWebSocket, useGameState
│   │   │   ├── pages/              # HomePage, BattlePage, LeaderboardPage, ReplayPage
│   │   │   └── types/              # 與後端共享的 TS 型別定義
│   │   ├── index.html
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   └── backend/                    # FastAPI
│       ├── api/
│       │   ├── routes/             # auth.py, leaderboard.py, replay.py
│       │   └── ws/                 # battle_ws.py (WebSocket endpoint)
│       ├── core/
│       │   ├── config.py           # 環境變數（pydantic-settings）
│       │   └── database.py         # AsyncSession, engine
│       ├── models/                 # SQLAlchemy ORM models
│       ├── schemas/                # Pydantic request/response schemas
│       ├── services/
│       │   ├── game/               # GameRoom, turn logic
│       │   ├── referee/            # LangGraph referee graph
│       │   └── npc/                # LangGraph NPC ReAct agent
│       └── main.py
│
├── docs/
│   ├── superpowers/specs/          # 設計規格文件（此檔所在）
│   └── architecture/               # 架構圖、ADR
├── docker-compose.yml              # PostgreSQL + Ollama 本地開發
├── .env.example
└── README.md
```

---

## 4. PostgreSQL Schema

### `players`
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | UUID PK | |
| username | VARCHAR(32) UNIQUE NOT NULL | |
| email | VARCHAR(255) UNIQUE | |
| password_hash | VARCHAR | bcrypt |
| wins | INT DEFAULT 0 | |
| losses | INT DEFAULT 0 | |
| total_damage | INT DEFAULT 0 | 排行榜依此排序 |
| created_at | TIMESTAMPTZ | |

### `matches`
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | UUID PK | 同時作為房間 ID |
| player1_id | UUID FK → players | NULL = AI NPC |
| player2_id | UUID FK → players | NULL = AI NPC |
| winner_id | UUID FK → players | NULL = 未結束 / 平局 |
| status | ENUM(pending, ongoing, finished) | |
| started_at | TIMESTAMPTZ | |
| ended_at | TIMESTAMPTZ | |

### `rounds`
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | UUID PK | |
| match_id | UUID FK → matches | |
| round_number | INT | |
| attacker_id | UUID FK → players | NULL = NPC 出招 |
| original_text | TEXT | 玩家原始輸入 |
| image_b64 | TEXT | 可為 NULL |
| display_text | TEXT | 裁判改寫後的嘲諷版 |
| damage | INT | |
| referee_comment | TEXT | |
| hp_snapshot | JSONB | `{"Player_1": 80, "Player_2": 65}` |
| created_at | TIMESTAMPTZ | |

### `npc_memory`
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | UUID PK | |
| opponent_id | UUID FK → players | 對哪個玩家的記憶 |
| attack_patterns | JSONB | 例：`["愛用圖攻擊", "常用問候句"]` |
| weaknesses | JSONB | 例：`["對圖攻擊反應差"]` |
| avg_damage_recv | FLOAT | NPC 平均受到的傷害 |
| round_count | INT | 與此玩家交手過幾回合 |
| updated_at | TIMESTAMPTZ | |

**設計重點：**
- `player1_id / player2_id = NULL` 代表 AI NPC，人機與人人對戰共用同一張表
- `rounds.hp_snapshot` 存每回合快照，回放直接還原每一幀
- `npc_memory` 是 NPC agent 的讀寫目標，每局結束後自動更新

---

## 5. LangGraph 設計

### 5.1 裁判 Graph（RefereeGraph）

**核心原則：只打一次 Ollama，其餘節點為純 Python。**

```
AttackInput (text + image?)
        │
        ▼
  [call_ollama]        ← 1 次呼叫，prompt 同時要求 damage + comment + display_text
        │
        ▼
  [parse_response]     ← 純 Python：JSON 解析 + markdown fence 清除 + 防呆
        │
        ▼
  [validate_clamp]     ← 純 Python：damage 夾在 10–30、comment 長度截斷
        │
        ▼
  RefereeResult(damage, comment, display_text)
```

**State 定義：**
```python
class RefereeState(TypedDict):
    original_text: str
    image_b64: str | None
    damage: int
    comment: str
    display_text: str
```

**失敗處理：** `parse_response` 解析失敗時回傳固定值 `(10, "裁判嘴瓢了")`，不重試（避免延遲加倍）。

### 5.2 NPC Agent（NPCAgent）

**架構：ReAct，單次 LLM 呼叫 + Python 工具節點。**

```
GameState (我方HP, 對手HP, 回合數, 對手最近 3 次攻擊)
        │
        ▼
  [get_opponent_memory]    ← 純 Python + DB 查詢（零 LLM 延遲）
        │
        ▼
  [call_ollama]            ← 1 次呼叫：think + generate_attack 合併
        │                    prompt 包含記憶摘要 + 當前戰況
        ▼
  [update_opponent_memory] ← 純 Python + DB 寫入（局後非同步執行）
        │
        ▼
  NPCAttack(text)  →  丟進 RefereeGraph 走裁判流程
```

**State 定義：**
```python
class NPCState(TypedDict):
    match_id: str
    opponent_id: str
    my_hp: int
    opponent_hp: int
    round_number: int
    recent_opponent_attacks: list[str]
    memory: dict            # 從 npc_memory 讀出
    strategy: str           # call_ollama 輸出的策略說明
    attack_text: str        # call_ollama 輸出的攻擊文字
```

**NPC 記憶邏輯：**
- 每回合開始：`get_opponent_memory` 取出對此玩家的歷史紀錄
- LLM prompt 包含記憶摘要：「對手愛用圖 → 這回合用密集文字嗆」
- 每局結束後：`update_opponent_memory` 非同步寫回 PostgreSQL
- 累積 5 局後，NPC 攻擊風格會明顯針對該玩家弱點

### 5.3 延遲評估

| 方案 | LLM 呼叫次數 | 預估等待 |
|---|---|---|
| 現有系統（單次呼叫） | 1 | ~3–6 秒 |
| 裁判 3 節點各一次（已捨棄） | 3（序列） | ~9–18 秒 |
| 本設計（1 LLM + Python 節點） | 1 | ~3–6 秒 |
| NPC agent（think+generate 合併） | 1 | ~3–6 秒 |

---

## 6. 前端設計

### 頁面結構

| 路由 | 頁面 | 說明 |
|---|---|---|
| `/` | HomePage | 登入/註冊、快速開局（真人 or AI NPC） |
| `/battle/:matchId` | BattlePage | 對戰主頁，WebSocket 連線 |
| `/leaderboard` | LeaderboardPage | 依累計傷害/勝場排行 |
| `/replay/:matchId` | ReplayPage | 從 rounds 表還原，時間軸滑桿逐幀播放 |

### BattlePage 版面

```
┌─────────────────────────────────┐
│  對手名稱          HP ████░░  65 │
│─────────────────────────────────│
│  [對話紀錄滾動區]                │
│  Player_1：你長得像... → 裁判：  │
│  「畫面有了」💥 -24              │
│  NPC：你媽媽... → 裁判：...      │
│─────────────────────────────────│
│  我方名稱          HP ████████ 80│
│─────────────────────────────────│
│  [ 輸入框 ] [📷 上傳圖] [出招！] │
└─────────────────────────────────┘
```

### WebSocket 訊息契約

```typescript
// 前端送出
type AttackPayload = { text: string; image?: string }

// 後端廣播
type ServerMessage =
  | { type: "system";     message: string; hp_status: HPMap; current_turn: string }
  | { type: "attack";     sender: string; display_text: string; damage: number;
      referee_comment: string; hp_status: HPMap; current_turn: string }
  | { type: "npc_attack"; display_text: string; damage: number;
      referee_comment: string; hp_status: HPMap }
  | { type: "game_over";  message: string; winner: string }
  | { type: "turn_error"; message: string }
```

---

## 7. 環境變數

```bash
# src/backend/.env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/verbal_sparring
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:12b
SECRET_KEY=<jwt signing key>

# src/frontend/.env.production
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

---

## 8. Cloudflare 部署

### Cloudflare Pages（前端）

```
GitHub repo 連接 Cloudflare Pages
Build command : npm run build
Build output  : dist
Root directory: src/frontend
```

### Cloudflare DNS（後端保護）

```
api.yourdomain.com  A/CNAME → 自架 server IP
                    橘色雲朵 proxy 開啟 → 隱藏真實 IP
```

### 本地開發（docker-compose）

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: verbal_sparring
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports: ["5432:5432"]

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

---

## 9. 核心依賴

| 類別 | 套件 |
|---|---|
| 後端框架 | fastapi, uvicorn, websockets |
| 資料庫 | sqlalchemy[asyncio], asyncpg, alembic |
| AI 推論 | langgraph, langchain-ollama |
| 認證 | python-jose, passlib[bcrypt] |
| 前端 | vite, react, react-router-dom, typescript |
| 前端 WS | 原生 WebSocket API（無需額外套件） |

---

## 10. 不在本次範疇

- 圖片內容審核（NSFW filter）
- 多語言支援
- 手機版 PWA
- 付費 / 訂閱機制
