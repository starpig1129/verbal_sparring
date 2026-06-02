# 唇槍舌戰 (Verbal Sparring)

雙人即時對戰的「嘴砲」格鬥遊戲。兩位玩家**輪流**出招 —— 打字或上傳圖片嗆對手，後端由本地 **Gemma 4 多模態 LLM** 扮演「毒舌裁判」，評估每次攻擊的傷害並給一句毒舌短評。傷害扣對手 HP，先把對手打到 0 獲勝。

## 玩法

- 兩位玩家分別以 `Player_1` / `Player_2` 進入同一個競技場。
- 回合制：`Player_1` 先手，出招結算後換對方；不是你的回合不能出招。
- 出招方式：
  - **打字**：輸入一句嗆對手的話。
  - **傳圖**：上傳一張圖（可附文字），裁判會看圖內容吐槽。
- 裁判（LLM）對每次攻擊回傳 `damage`（傷害）+ 一句毒舌短評，傷害扣對手 HP。
- 任一方 HP 歸零 → 遊戲結束，自動重置開新局。

## 架構

四個部分，三層應用 + 一個常駐模型服務：

```
battle.html  ── ws://host/ws/battle/{player_id} ──▶  app.py (FastAPI)
 (瀏覽器前端                                          房間 / 回合制 / 廣播
  WebSocket client)                                       │ import
                                                          ▼
                                            referee_core.*.so  (Cython 編譯)
                                             裁判推論引擎 = vLLM HTTP client
                                                          │ POST /v1/chat/completions
                                                          ▼
                                            vLLM serve  (常駐，port 8001)
                                             gemma-4-E4B-it AWQ/INT8 多模態模型
```

重點：

- **`referee_core` 是 source `.py`，runtime 載入的是同名 `.so`**。改 `referee_core.py` 後必須 `python setup.py build_ext --inplace` 重編，否則不生效。
- **模型不在遊戲 process 內**。由 vLLM 常駐載入，`referee_core` 只是個 HTTP client，所以遊戲 server 啟動是秒級的（不需載模型）。

## 專案結構

| 檔案 | 角色 |
|---|---|
| `app.py` | FastAPI server：WebSocket 連線、單一房間、回合制、廣播。 |
| `battle.html` | 純靜態前端，WebSocket client + 血條 / 回合 UI。 |
| `referee_core.py` | 裁判推論引擎 source（vLLM HTTP client）。**改完要重編 `.so`**。 |
| `setup.py` | Cython 編譯設定，產出 `referee_core.*.so`。 |
| `vision_probe.py` | 獨立的多模態探針腳本：在本機直接載 Gemma 驗證圖片辨識 / 量化效果，**與遊戲執行期無關**，是除錯 / 調校量化方式用的工具。 |
| `requirements.txt` | 依用途分組的 Python 依賴。 |

> 編譯產物（`build/`、`*.so`、`referee_core.c`）與 `__pycache__/` 已 gitignore，clone 後用 `setup.py` 自行重編。

## 函式庫 API：`referee_core`

整個函式庫對外只暴露一個公開函式：

```python
ai_referee_engine(original_text: str, image_data_url: str | None = None) -> tuple[int, str]
```

| 參數 | 說明 |
|---|---|
| `original_text` | 玩家發言文字。純傳圖時可為空字串 `""`。 |
| `image_data_url` | 選填。圖片的 data URL（`data:image/png;base64,...`）。傳圖出招用。 |

**回傳** `(damage, referee_comment)`：

- `damage`：`int`，已夾在 `1–50`。
- `referee_comment`：`str`，裁判毒舌短評。

行為：組多模態 chat messages（含 few-shot 引導 JSON 格式）打 vLLM，解析回傳的 JSON。vLLM 連線失敗或 JSON 解析失敗時，回傳 fallback 短評並扣固定傷害（不會讓遊戲崩潰）。

> 其餘 `_` 開頭的（`_build_messages`、`_extract_json`、`_SYSTEM_BLOCK`、`_FEW_SHOT`）是私有實作，不算對外 API。

## Web API：`app.py`

| 接口 | 說明 |
|---|---|
| `GET /` | 回傳 `battle.html`（遊戲頁面） |
| `WebSocket /ws/battle/{player_id}` | 對戰連線，`player_id` 用 `Player_1` / `Player_2` |
| `GET /docs`、`/redoc`、`/openapi.json` | FastAPI 自動產生的接口 |

WebSocket 協定：

- **Client → Server**：`{"text": "...", "image": "data:image/...;base64,..."（選填）}`
- **Server → Client**（廣播）：依 `type` 分類
  - `system`：系統訊息（進場 / 離場 / 新局開始）
  - `attack`：出招結果 — `sender`、`display_text`、`display_image`、`damage`、`referee_comment`、`hp_status`、`current_turn`
  - `turn_error`：非當前回合方出招被擋（只回該玩家）
  - `game_over`：某方 HP 歸零
  - 前三種都帶 `hp_status` 與 `current_turn`，前端據此更新血條與「輪到誰」的輸入鎖定。

## 執行方式

**0. 取得專案 + 安裝依賴**

```bash
git clone git@github.com:JuhanWu/verbal_sparring.git
cd verbal_sparring
pip install -r requirements.txt   # torch/transformers 等視覺探針依賴可選，見下方「依賴」
```

**1. 啟動 vLLM 模型服務（port 8001）**

```bash
vllm serve /media/dalin/data/models/gemma-4-E4B-it-AWQ-INT8 \
  --port 8001 --served-model-name gemma4-referee \
  --gpu-memory-utilization 0.90 --max-model-len 4096 --enforce-eager
```

**2. 編譯裁判引擎**（只有改過 `referee_core.py` 才需要）

```bash
python setup.py build_ext --inplace
```

**3. 啟動遊戲 server（port 8000）**

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

**4. 開始對戰**：瀏覽器開 `http://localhost:8000/`，用兩個分頁分別選 `Player 1` / `Player 2`。

## 依賴

- **遊戲 server / 裁判引擎**：`fastapi`、`uvicorn`、`requests`、`cython`、`setuptools`
- **模型服務**：`vllm`（0.20.x）+ 本地 `gemma-4-E4B-it` AWQ/compressed-tensors INT8 權重
- 遊戲 process 本身**不需要** `torch` / `transformers`（模型都在 vLLM 那邊）

完整版本鎖定見 [`requirements.txt`](requirements.txt)，分三組：**server 執行期**（fastapi / uvicorn / websockets / requests）、**Cython 編譯**（cython / setuptools）、**視覺探針選用**（torch / transformers / Pillow / bitsandbytes / accelerate，只有跑 `vision_probe.py` 才需要）。`vllm` 與模型權重需另外自備，不在 `requirements.txt` 內。

## 注意事項

- **量化方式很關鍵**：必須用 **vision tower 不量化** 的 INT8 版（這個 AWQ/compressed-tensors 版把 `vision_tower` / `audio_tower` 排除在量化外）。先前用 bitsandbytes NF4 全量化會把視覺搞壞（純色看成灰、認不出圖片內容）。
- **`--enforce-eager`**：目前環境 torch.compile 的 triton kernel 編譯有問題（map segment 失敗），用 `--enforce-eager` 繞過。代價是沒有 CUDA graph 優化，單次推論約 7 秒。
- **單一房間**：`GameRoom` 是 single global instance，整個 server 只跑一場對戰、玩家固定 `Player_1` / `Player_2`。多房間需另外擴充。
</content>
