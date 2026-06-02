# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案性質

一個雙人即時對戰的「唇槍舌戰」WebSocket 小遊戲。兩位玩家透過 WebSocket 連線到 FastAPI server，輸入要噴對方的話，後端用本地 Gemma LLM 當「毒舌裁判」做兩件事：

1. 把和平的問候竄改成嘲諷句（保留主題）
2. 評估傷害 (10–30 整數) 並給簡短毒舌短評

LLM 推論邏輯刻意被編譯成 `.so` 隱藏 — 設計目的是不讓前端 / 客戶端拿到 system prompt 與模型細節。

## 架構（三層）

```
battle.html  ──ws/battle/{player_id}──▶  app.py (FastAPI)  ──import──▶  referee_core.cpython-313-*.so
  (前端 WS client)                        (連線 / 房間 / 廣播)              (Cython 編譯：載入 Gemma + ai_referee_engine)
```

關鍵設計點：

- **`referee_core.py` 是 source，但 runtime 載入的是同名 `.so`**。Python import 機制下 `.so` 優先於 `.py`，所以修 `.py` 不會生效，必須重編。`app.py:7` 的 `import referee_core` 拿到的是編譯版。
- **模型在 module import 階段就 load 進 GPU**（`referee_core.py:11-23`），不是 lazy。第一次 import `referee_core` 會吃掉啟動時間 + VRAM；server 啟動後常駐。
- **房間是 single global instance**（`app.py:28` 的 `room = GameRoom()`）。整個 server 只能跑一個對戰，兩位玩家用 hardcoded `Player_1` / `Player_2` 區分。要做多房間需要改架構。
- **HP 重置時機**：任一方 HP 歸零後 `room.hp` 立刻被重置成 `{Player_1: 100, Player_2: 100}`（`app.py:67`），但 `active_connections` 不會斷，玩家可以直接繼續打下一局。
- **LLM 輸出走 JSON 解析 + 防呆**（`referee_core.py:62-77`）：清掉 markdown fence 後 `json.loads`，失敗就回固定的「系統發生時空錯亂」訊息扣 10 血。

## 常用指令

### 編譯 Cython `.so`

每次改 `referee_core.py` 都要重編，server 才會載到新版本：

```bash
python setup.py build_ext --inplace
```

產出 `referee_core.cpython-313-x86_64-linux-gnu.so`（與 Python 版本綁定，目前是 3.13）。

### 啟動 server

repo 內沒有寫明啟動指令，FastAPI 標準作法：

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

`--reload` 在開發階段有用，但注意它會觸發 `referee_core` 重 import → 重新把 Gemma 載一次到 GPU。

### 前端

`battle.html` 是純靜態 HTML，瀏覽器直接開即可。注意 WebSocket URL 寫死，要根據 server host/port 修改 client 程式碼裡的 ws URL。

## 已知 / 重要狀態

- **`battle.html` 未寫完**（檔案在 62 行截斷，缺 `<button>` send、`<script>` 區、closing tags）。如果要做前端 demo 必須先補完。
- **`MODEL_NAME = "google/gemma-4-E4B"`**（`referee_core.py:9`）— 這是 HuggingFace 路徑寫法但實際模型名可能要對齊使用者環境（user CLAUDE.md 提到本地是 `gemma-4-E4B-it-AWQ-INT8`，需要時改成本地路徑或對應的 AWQ repo）。
- **沒有 `requirements.txt` / `pyproject.toml`**。依賴至少包含：`fastapi`, `uvicorn`, `websockets`, `torch`, `transformers`, `cython`, `setuptools`。
- **不是 git repo**（無 `.git`）。
- **沒有 test**。

## 修改流程提醒

改 `referee_core.py` 的 prompt 或推論邏輯 → 一定要先重跑 `python setup.py build_ext --inplace` → 重啟 server 才生效。改 `app.py` 直接 `--reload` 即可（但會觸發模型重 load）。
