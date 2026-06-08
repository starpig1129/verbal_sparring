# Cloudflare 部署指南

## 前端 — Cloudflare Pages

1. 在 [Cloudflare Pages](https://pages.cloudflare.com) 建立新專案
2. 連接 GitHub repo
3. 設定 Build configuration：
   - Framework preset: Vite
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `src/frontend`
4. 在 Cloudflare Pages 的 Settings > Environment variables 加入（請依據您的後端網址設定，必須為 HTTPS/WSS，以符合瀏覽器安全性要求）：
   - `VITE_API_URL` = `https://api.yourdomain.com`
   - `VITE_WS_URL` = `wss://api.yourdomain.com`
   *(備註：後端已在 `src/backend/main.py` 中啟用 `CORSMiddleware` (Allow Origins: `*`)，可完美支援來自任何 Cloudflare Pages 部署網域的跨網域 API 與 WebSocket 連線。)*
5. 每次 push 到 main branch 自動觸發部署

## 後端 — Cloudflare Tunnel 部署 (隱藏 IP 且無須對外開 Port)

若您的網域在另一個 Cloudflare 帳號下，最安全且推薦的做法是使用 Cloudflare Tunnel。您不需要在防火牆開放 8000 port，後端伺服器也完全不會暴露真實 IP。

### 步驟 1：登入與建立 Tunnel
1. 在終端機執行 `cloudflared tunnel login` 完成登入授權（若已有既存憑證，請先備份舊憑證或直接使用該帳戶）。
2. 建立名為 `vs-tunnel` 的通道：
   ```bash
   cloudflared tunnel create vs-tunnel
   ```
3. 將子網域 `api-vs.spkuan.cc` 指向該 Tunnel：
   ```bash
   cloudflared tunnel route dns vs-tunnel api-vs.spkuan.cc
   ```

### 步驟 2：配置設定檔 (config.yml)
在 `~/.cloudflared/config.yml` 寫入以下內容：
```yaml
tunnel: vs-tunnel
credentials-file: /etc/cloudflared/credentials.json
ingress:
  - hostname: api-vs.spkuan.cc
    service: http://backend:8000
  - service: http_status:404
```

### 步驟 3：啟動 Docker 容器
在 `src/backend/.env` 中配置您本地的憑證路徑（預設為 `~/.cloudflared`，但可視主機路徑進行調整以防洩露）：
```env
CLOUDFLARED_DIR=/mnt/users/ziyue/.cloudflared
```
在 `docker-compose.dev.yml` 中已配置 `tunnel` 服務將該目錄動態掛載至容器內，並執行 Tunnel。直接啟動即可：
```bash
docker compose -f docker-compose.dev.yml up --build -d
```
*(請確保您的 Cloudflare 帳號已開啟 WebSocket 代理支援以確保即時對戰功能運作)*

## 後端 — 傳統 Cloudflare DNS proxy (備用方式)

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
