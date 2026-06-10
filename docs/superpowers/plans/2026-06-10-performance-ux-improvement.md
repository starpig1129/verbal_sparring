# 唇槍舌戰：運作效能與遊玩體驗改善計畫

> 日期：2026-06-10
> 範圍：後端（FastAPI / LangGraph / PostgreSQL）、前端（React / Vite）、AI 推論（Ollama / vLLM）、部署（Cloudflare）
> 依據：對 `src/backend/api/ws/battle_ws.py`、`services/game/battle_session.py`、`services/referee/graph.py`、`core/database.py`、前端 hooks 與頁面的全面程式碼審視。

---

## 總覽：玩家感受到的延遲從哪來

一回合 NPC 對戰在伺服器端依序執行三次 LLM 推論。現有的 node-level streaming 已在每個階段完成時立即 broadcast，前端也已有完整的狀態回饋（樂觀泡泡、pending 跳動動畫、各事件音效）：

```
玩家送出（前端立即顯示樂觀泡泡＋音效）
  → 裁判 LLM 評分玩家攻擊    完成即 broadcast attack（傷害、HP 立即更新）
  → NPC LLM 生成回擊文字      完成即 broadcast npc_typing（NPC 泡泡先現身）
  → 裁判 LLM 評分 NPC 攻擊    完成即 broadcast npc_attack（傷害、HP、換玩家）
```

問題不在「玩家不知道現在的狀態」——回饋層已經做得到位。問題在**每一段等待本身的長度**：三次 12B 推論序列執行、各自等整段文字生成完才進入下一段，玩家要等三段全部跑完才能再次出手。縮短這條序列鏈是效能改善的主軸；其餘延遲來自 DB 查詢無索引、每回合多次 commit、以及未壓縮的 base64 圖片在 WS 與 prompt 間搬運。

改善依「影響大、風險低」優先排序，分三個 Phase。

---

## Phase 1：推論延遲（最大瓶頸，預估體感改善 30–50%）

### 1.1 NPC 生成與玩家攻擊評分並行化

**問題**：`battle_session.py` 的 graph 是 `score_player_attack → npc_generate → npc_score` 純序列。但 `_node_npc_generate` 只需要玩家的攻擊文字與對話歷史，**不需要裁判的評分結果**（`battle_session.py:165-200` 只讀 hp、memory、messages）。

**做法**：把 graph 改為 fan-out——`score_player_attack` 與 `npc_generate` 同時啟動，`npc_score` 等兩者完成後執行（它需要玩家評分後的 HP 來組 prompt，以及 NPC 文字）：

```
entry ─┬─ score_player_attack ─┐
       └─ npc_generate ────────┴─ npc_score → END
```

注意事項：
- 玩家攻擊若直接打死 NPC（`game_over`），需丟棄已並行啟動的 NPC 回合結果——在 `npc_score` 入口檢查 `game_over` 即可。
- HP 用於 NPC prompt 的數值會是「評分前」的 HP，對嗆聲品質影響極小，可接受；若在意，讓 `npc_generate` 不含 HP、由 `npc_score` 統一處理。
- **broadcast 順序需保留**：並行後 `npc_generate` 可能先於 `score_player_attack` 完成，WS 端要把 `npc_typing` 緩存到玩家攻擊結果送出後再 broadcast，維持「先看到自己的傷害、再看到 NPC 回嗆」的現有敘事順序。
- Ollama 單卡同時跑兩個請求會互搶資源；需設 `OLLAMA_NUM_PARALLEL=2`（同模型 batch 推論，throughput 仍優於序列）。vLLM 天生支援 continuous batching，收益最大。

**預估**：每回合省掉一整段「NPC 生成」的等待（數秒），體感從「三段等待」變「兩段」。

### 1.2 Token-level streaming：NPC 文字逐字顯示

**問題**：node-level streaming 讓每個階段完成時立即顯示，但「階段內」仍是一次到位——NPC 泡泡要等整段文字生成完（`npc_typing`）才出現，生成期間的等待無法再縮短給玩家看。

**做法**：
- `_generate_npc_attack` 改用 `llm.astream()`，把 token chunk 透過新的 WS 訊息型別（`npc_streaming`，含遞增文字片段）即時推送；NPC 泡泡從首 token 就現身、逐字長出。
- 裁判輸出是 JSON、無法直接逐字顯示，維持整段不動。若日後想 stream 裁判評語，需改輸出格式為「先評語文字、再尾隨 JSON 區塊」，有 prompt 重調風險，列為後續實驗。
- 前端 `useGameState` 增加 streaming entry：收到 chunk 時更新同一個 pending bubble 的文字。

**預估**：NPC 文字的首 token 約 1–2 秒內出現，把最長一段等待（NPC 生成全文）攤平成逐字進度。

### 1.3 Ollama / vLLM 推論參數調校

**問題**：`make_chat_llm()`（`core/config.py:96`）未設任何推論參數。

**做法**：
- **`keep_alive: "30m"`**（ChatOllama 參數）：預設 5 分鐘閒置就卸載模型，下一位玩家要等數十秒冷啟動重載 12B。低流量期這是最嚴重的隨機延遲來源。
- **`num_predict`（max tokens）上限**：裁判輸出 JSON 約 100–150 token、NPC 嗆聲約 80–120 token，設 256 上限防止偶發的長篇生成把回合拖到 30 秒以上。
- **`num_ctx` 明確設定**（如 4096）：配合 1.4 的歷史截斷，避免 context 超限時 Ollama 靜默截掉 system prompt。
- vLLM 路徑：確認啟動參數開啟 `--enable-prefix-caching`——裁判的 system prompt + few-shots 每次呼叫都相同，prefix cache 可跳過這段的 prefill，對 TTFT 改善顯著。

### 1.4 限制 NPC prompt 的歷史長度

**問題**：`_generate_npc_attack` 把 `state["messages"]` 全部塞進 prompt（`battle_session.py:197`）。「局終自動再戰」會沿用同一 session，messages 無上限增長 → 回合越打越慢，且可能擠掉 system prompt。

**做法**：只取最近 N 輪（建議 12 則訊息）+ 開場 2 則（保留對戰基調）。裁判已只取最近 4 則，不用動。

### 1.5 圖片攻擊瘦身

**問題**：`AttackInput.tsx` 用 `readAsDataURL` 原樣上傳，手機照片可達 5–10 MB base64，經 WS 傳輸 → 塞進 vision prompt → 原樣存進 `rounds.image_b64` TEXT 欄位。拖慢上傳、推論與之後所有 history 查詢。

**做法**：
- 前端：canvas 縮圖至最長邊 768px、JPEG quality 0.8 再轉 base64（vision 模型輸入也用不到更高解析度）。
- 後端：WS 訊息大小上限檢查（如 1 MB），超過回 error。

---

## Phase 2：後端正確性與資源效率

### 2.1 WebSocket 連線不再終生持有 DB session

**問題**：`battle_ws()` 用 `Depends(get_session)` 取得 session，整個 WS 生命週期（可能數十分鐘）持有它。engine 未設 pool 參數（`database.py:21`，asyncpg 預設 pool_size=5）。**5 個玩家掛在對戰頁，第 6 條連線就會卡死等 pool**。

**做法**：
- WS handler 內改為每次 DB 操作用短命 session：`async with SessionFactory() as db: ...`（連線驗證、persist_round、finish_match 各自開關）。
- `make_engine` 加上 `pool_size=10, max_overflow=20, pool_pre_ping=True`。
- `LangGraph config` 傳遞的 `db` 同步改為由節點自行開 session，或傳 factory。

### 2.2 修復背景記憶分析的 session 競態

**問題**：`_do_game_over`（`battle_ws.py:129`）用 `asyncio.create_task(analyze_and_update_player_memory(db, ...))` 把 **WS handler 的同一個 session** 丟給背景任務。任務真正執行時 WS 可能已斷線、session 已關閉 → 記憶分析靜默失敗；即使沒關閉，兩個協程共用一個 AsyncSession 本身就是競態。

**做法**：背景任務內自行 `async with SessionFactory() as db:` 開新 session；任務引用收集到 module-level set 防止被 GC，並加 done-callback 記錄例外。

### 2.3 broadcast 防呆與並行送出

**問題**：`GameRoom.broadcast()`（`room.py:56`）序列 `await send_text`，任一 dead socket 拋例外會**中斷迴圈，後面的玩家收不到訊息**，且例外直接炸到呼叫端。

**做法**：`asyncio.gather(*sends, return_exceptions=True)`，失敗的連線從 `connections` 移除。

### 2.4 每回合 DB 寫入合併 + 索引

**問題**：
- 每次玩家攻擊有兩次 commit：`_persist_round` 一次、`total_damage` 更新一次（`battle_ws.py:423-435`），且 `total_damage` 更新前還先 SELECT 整個 Player row。
- `rounds.match_id` 無索引——每次 WS 連線（含重連）都全表掃描撈 history；`matches.player1_id/player2_id/status` 也無索引（match history API 會用到）。
- history 查詢 `select(GameRound)` 撈出**所有欄位包含 image_b64**——一場有圖片的對戰，重連一次就搬幾 MB。

**做法**：
- 合併為單一 transaction；`total_damage` 改用 `update(Player).where(...).values(total_damage=Player.total_damage + dmg)` 免 SELECT。
- Alembic migration：`rounds(match_id)`、`matches(player1_id)`、`matches(player2_id)`、`matches(status)` 加索引。
- history 查詢改 `select(GameRound).options(defer(GameRound.image_b64))` 或明確指定欄位。

### 2.5 局終「再來一局」改建新 match

**問題**：`_do_game_over` 後 `room.reset()` 在**同一個已標記 finished 的 match** 上繼續對戰：round_number 歸零後 `_persist_round` 繼續往同一 match_id 寫入 → rounds 出現重複 round_number、replay 與戰績資料混亂，且第二局的勝負不會更新 wins/losses（match 已 finished，`_finish_match` 提前 return）。

**做法**：局終時不自動 reset；改為 broadcast `game_over` 後由前端 GameOverModal 提供「再戰一局」按鈕 → 呼叫既有 `POST /api/matches` 建新 match → 雙方導向新 battle URL。順帶解決 BattleSession messages 無限增長（1.4）的根因。

### 2.6 配對佇列去重與防競態

**問題**：`queue_ws` 的配對邏輯複製了兩份（連線初始化與 `start_matchmaking`，`battle_ws.py:582-628` vs `643-692`）；兩位玩家在 `await db.commit()` 期間同時掃描 `online_players` 可能互相配對兩次（建出兩場 match）。

**做法**：抽成單一 `try_matchmake(player_uuid)` 函式，用 module-level `asyncio.Lock` 包住「掃描＋標記 is_searching=False」的臨界區（單進程下足夠）。

### 2.7 print → logging

全後端用 `print(..., flush=True)`；改用 `logging`（uvicorn handler），戰鬥事件 INFO、錯誤 ERROR 含 traceback，方便上線後追查延遲與錯誤。低風險、機械性修改。

---

## Phase 3：遊玩體驗（前端為主）

### 3.1 心跳與自動重連（Cloudflare 部署下的必修課）

**問題**：
- battle WS 完全沒有 ping/pong；**Cloudflare proxy 對 idle 約 100 秒的 WS 會直接切斷**。對手思考超過一分多鐘，你的連線就默默死了，而且 `useWebSocket.ts` 沒有任何重連邏輯——畫面永遠卡住。
- 後端已有完整的 history 恢復機制（`battle_ws.py:275-292`），但前端斷線後不會重連去觸發它。

**做法**：
- 前端 `useWebSocket`：每 30 秒送 `{"type":"ping"}`；`onclose` 時以 exponential backoff（1s/2s/4s…上限 30s）自動重連，並暴露 `connectionState` 給 UI。
- 後端 battle WS 訊息迴圈處理 `ping` → 回 `pong`（queue WS 已有，battle WS 沒有）。
- BattlePage 顯示連線狀態列（「連線中斷，重新連線中…」），重連成功後靠既有 history 訊息無縫恢復戰況。

### 3.2 錯誤與回合提示優化

- `turn_error`、`error` 目前塞進 chat log（`useGameState.ts:91`），會被洗版淹沒 → 改 toast（自動消失，不污染對戰記錄）。
- 對戰中的動畫與音效回饋已完整（樂觀泡泡、pending 動畫、受擊/出擊音效），唯一缺口是**玩家切到其他分頁時**收不到提示 → 輪到自己時加瀏覽器 tab title 閃爍（PvP 等對手久時最有用）。
- 回合計時器（如 90 秒）：先做純前端倒數提示防掛機感；後端強制跳過回合列為後續（需服務端計時器與 timeout 廣播）。

### 3.3 對戰記錄與長對話效能

- `chatLog` 無上限增長且每則訊息觸發整個列表 re-render；長對戰（含再戰）會卡。MessageBubble 加 `React.memo`，超過 200 則時虛擬化（`@tanstack/react-virtual`）或截斷顯示「載入更早記錄」。
- 戰績目前 localStorage 與 DB 雙軌（`BattlePage.tsx:47-60` 寫 localStorage，ProfilePage 又打 API）→ 統一走 DB（match history API 已存在），刪 localStorage 路徑。

### 3.4 大廳體驗

- HomePage 每 10 秒輪詢 `/api/matches/players`，玩家上下線最多延遲 10 秒且浪費請求 → 既然每個玩家都掛著 queue WS，改由 `online_players` 變動時主動 broadcast `player_list_update`（單進程內成本極低），輪詢留作 fallback。（配對等待動畫、計時與 `playMatchFound` / `playMatchChallenge` 音效均已存在，不需重做。）

### 3.5 遊戲性平衡（選做，與效能無關但影響留存）

- 傷害僅 10–30、固定 100 HP → 每局 4–10 回合，且裁判常給中間值，攻擊好壞體感差異小。可考慮：暴擊機制（裁判給 28+ 時觸發特效與額外 5 點傷害）、連擊獎勵（連續高分傷害遞增）、每局隨機「主題回合」（切題加成）。
- 這些只動 `_score` 後處理與前端特效，不需重訓模型。建議先上暴擊特效（純表現層，零平衡風險）再觀察。

---

## 不在本計畫範圍（記錄備查）

- **水平擴展**：`rooms` / `_sessions` / `online_players` 全是進程內 dict，多 worker 或多機需 Redis（pub/sub + 共享狀態）。目前單機單進程流量下不值得做，但 2.x 的修改應避免加深耦合（如 2.6 的 Lock 註明單進程假設）。
- **模型更換/重訓**：LoRA 訓練管線（`training/`）的品質改善另案處理。
- **token 放 query string 的安全性**：已知取捨（WS header 限制），維持現狀。

---

## 實施順序與驗證

| 順序 | 項目 | 風險 | 驗證方式 |
|---|---|---|---|
| 1 | 1.3 keep_alive / num_predict | 極低 | 閒置 10 分鐘後攻擊，回合延遲不出現冷啟動尖峰 |
| 2 | 2.2 背景任務 session、2.3 broadcast 防呆 | 低 | `pytest src/backend/tests/`；模擬一方斷線後另一方仍收到訊息 |
| 3 | 2.4 索引 + 合併 commit + defer image | 低 | Alembic upgrade/downgrade 雙向通過；EXPLAIN 確認走索引 |
| 4 | 2.1 短命 session + pool 設定 | 中 | 併發 10 條 WS 連線壓測不卡 pool |
| 5 | 3.1 心跳 + 自動重連 | 中 | 手動斷網 30 秒，畫面顯示重連並恢復戰況 |
| 6 | 1.1 NPC 並行化 | 中 | 計時對比：同一攻擊文字回合總時長下降；game_over 時無 NPC 殘留訊息 |
| 7 | 1.2 NPC streaming | 中 | 首 token < 2s 出現在畫面 |
| 8 | 2.5 再戰建新 match、2.6 配對鎖 | 中 | 再戰後 DB 出現新 match row；雙人同時配對只建一場 |
| 9 | 1.4 / 1.5 / 2.7 / 3.2–3.4 | 低 | 各自的單元測試 + 手動驗證 |

每一步獨立可上線、可回滾；後端改動跑 `pytest`（`tests/` 已有 WS 與 game room 覆蓋），前端跑 `npm test` 與 `npm run build`。

效能基準：實施前先在 `evaluation/` 記錄一份基準——NPC 對戰 10 回合的每回合延遲（p50/p95）、WS 連線恢復時間、history 查詢耗時，每完成一個 Phase 重測一次。
