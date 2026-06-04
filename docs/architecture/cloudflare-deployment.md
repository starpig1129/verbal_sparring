# Cloudflare 部署指南

## 前端 — Cloudflare Pages

1. 在 [Cloudflare Pages](https://pages.cloudflare.com) 建立新專案
2. 連接 GitHub repo
3. 設定 Build configuration：
   - Framework preset: Vite
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `src/frontend`
4. 在 Cloudflare Pages 的 Settings > Environment variables 加入：
   - `VITE_API_URL` = `https://api.yourdomain.com`
   - `VITE_WS_URL` = `wss://api.yourdomain.com`
5. 每次 push 到 main branch 自動觸發部署

## 後端 — Cloudflare DNS proxy

1. 在 Cloudflare DNS 新增一筆 A record：
   - Name: `api`
   - IPv4 address: `<你的 server IP>`
   - Proxy status: 橘色雲朵（Proxied）→ 隱藏真實 IP
2. 在 server 上啟動 FastAPI：
   ```bash
   cd src/backend && uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. Cloudflare Free plan 預設只代理 HTTP/HTTPS（80/443）。
   WebSocket 需要在 Cloudflare Network 設定中確認 WebSockets 已開啟。

## 本地開發啟動

```bash
# 啟動 PostgreSQL + Ollama（若本地沒裝）
docker compose up -d postgres ollama

# 下載 Ollama 模型（第一次）
docker compose exec ollama ollama pull gemma4:12b

# 後端
cp .env.example src/backend/.env  # 填入 SECRET_KEY
cd src/backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端（另一個終端機）
cd src/frontend && npm run dev
```

瀏覽器開啟 http://localhost:5173
