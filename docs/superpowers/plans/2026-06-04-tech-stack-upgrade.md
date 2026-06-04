# 唇槍舌戰技術棧升級實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將現有單檔 FastAPI + 純 HTML 升級為 Vite React + FastAPI + PostgreSQL + LangGraph + Ollama 完整技術棧，支援多房間對戰、玩家帳號、AI NPC 對手、排行榜與對戰回放。

**Architecture:** FastAPI 管理 WebSocket 即時遊戲迴圈與 REST API；PostgreSQL（SQLAlchemy async）做完整持久化；LangGraph 包裝裁判 graph 與 NPC agent，各只打一次 Ollama（gemma4:12b）；Vite React 前端部署至 Cloudflare Pages，後端透過 Cloudflare CDN/DNS proxy 保護。

**Tech Stack:** Python 3.13, FastAPI 0.115+, SQLAlchemy 2 (asyncio), asyncpg, Alembic, LangGraph 0.2+, langchain-ollama, python-jose[cryptography], passlib[bcrypt], pytest, pytest-asyncio, httpx; Vite 5, React 18, TypeScript 5, react-router-dom v6, vitest, @testing-library/react; PostgreSQL 16, Ollama (gemma4:12b), Docker Compose

---

## 檔案結構總覽

```
verbal_sparring/
├── src/
│   ├── backend/
│   │   ├── tests/
│   │   │   ├── conftest.py              # pytest fixtures
│   │   │   ├── test_auth.py
│   │   │   ├── test_matches.py
│   │   │   ├── test_referee.py
│   │   │   ├── test_npc.py
│   │   │   ├── test_game_room.py
│   │   │   ├── test_websocket.py
│   │   │   └── test_api.py              # leaderboard + replay
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── matches.py
│   │   │   │   ├── leaderboard.py
│   │   │   │   └── replay.py
│   │   │   └── ws/
│   │   │       ├── __init__.py
│   │   │       └── battle_ws.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── player.py
│   │   │   ├── match.py
│   │   │   ├── game_round.py
│   │   │   └── npc_memory.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── match.py
│   │   │   ├── leaderboard.py
│   │   │   └── replay.py
│   │   ├── services/
│   │   │   ├── auth.py                  # JWT + password helpers
│   │   │   ├── game/
│   │   │   │   └── room.py              # GameRoom class
│   │   │   ├── referee/
│   │   │   │   └── graph.py             # LangGraph referee
│   │   │   └── npc/
│   │   │       └── agent.py             # LangGraph NPC agent
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   └── env.py
│   │   ├── alembic.ini
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── pytest.ini
│   └── frontend/
│       ├── src/
│       │   ├── types/
│       │   │   └── game.ts              # 共享 TS 型別
│       │   ├── hooks/
│       │   │   ├── useWebSocket.ts
│       │   │   └── useGameState.ts
│       │   ├── components/
│       │   │   ├── HPBar.tsx
│       │   │   ├── ChatLog.tsx
│       │   │   └── AttackInput.tsx
│       │   ├── pages/
│       │   │   ├── HomePage.tsx
│       │   │   ├── BattlePage.tsx
│       │   │   ├── LeaderboardPage.tsx
│       │   │   └── ReplayPage.tsx
│       │   ├── App.tsx
│       │   └── main.tsx
│       ├── index.html
│       ├── package.json
│       ├── vite.config.ts
│       └── tsconfig.json
├── docs/
│   └── superpowers/
│       ├── specs/
│       └── plans/                       # 此檔所在
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Task 1: 基礎設施 — Docker Compose + 環境變數 + 資料夾骨架

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `src/backend/requirements.txt`
- Create: 所有空的 `__init__.py`（packages）

- [ ] **Step 1: 建立資料夾骨架**

```bash
mkdir -p src/backend/{api/routes,api/ws,core,models,schemas,services/game,services/referee,services/npc,tests,alembic/versions}
mkdir -p src/frontend/src/{types,hooks,components,pages}
mkdir -p docs/superpowers/{specs,plans}
touch src/backend/api/__init__.py
touch src/backend/api/routes/__init__.py
touch src/backend/api/ws/__init__.py
touch src/backend/core/__init__.py
touch src/backend/models/__init__.py
touch src/backend/schemas/__init__.py
touch src/backend/services/__init__.py
touch src/backend/services/game/__init__.py
touch src/backend/services/referee/__init__.py
touch src/backend/services/npc/__init__.py
```

- [ ] **Step 2: 建立 `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: verbal_sparring
      POSTGRES_USER: vsuser
      POSTGRES_PASSWORD: vspass
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vsuser -d verbal_sparring"]
      interval: 5s
      timeout: 5s
      retries: 5

  postgres_test:
    image: postgres:16
    environment:
      POSTGRES_DB: verbal_sparring_test
      POSTGRES_USER: vsuser
      POSTGRES_PASSWORD: vspass
    ports:
      - "5433:5432"

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

volumes:
  pg_data:
  ollama_data:
```

- [ ] **Step 3: 建立 `.env.example`**

```bash
# src/backend/.env (copy from here)
DATABASE_URL=postgresql+asyncpg://vsuser:vspass@localhost:5432/verbal_sparring
TEST_DATABASE_URL=postgresql+asyncpg://vsuser:vspass@localhost:5433/verbal_sparring_test
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:12b
SECRET_KEY=change-this-to-a-random-32-char-string
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# src/frontend/.env.development (copy from here)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# src/frontend/.env.production (fill in your domain)
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

- [ ] **Step 4: 建立 `src/backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
websockets==14.1
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0
langgraph==0.2.50
langchain-ollama==0.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic-settings==2.6.1

# dev / test
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.0
```

- [ ] **Step 5: 啟動 Docker 服務確認可連線**

```bash
docker compose up -d postgres postgres_test
docker compose ps
```

Expected: postgres 與 postgres_test 狀態為 `healthy` / `running`。

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example src/backend/requirements.txt src/backend/
git commit -m "feat: project scaffold, docker-compose, requirements"
```

---

## Task 2: 後端基礎 — config、database、main.py

**Files:**
- Create: `src/backend/core/config.py`
- Create: `src/backend/core/database.py`
- Create: `src/backend/main.py`
- Create: `src/backend/tests/conftest.py`
- Create: `src/backend/pytest.ini`

- [ ] **Step 1: 建立 `src/backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 2: 建立 `src/backend/core/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    test_database_url: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:12b"
    secret_key: str
    access_token_expire_minutes: int = 10080

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

- [ ] **Step 3: 建立 `src/backend/core/database.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

def make_engine(url: str):
    return create_async_engine(url, echo=False)

def make_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)

from src.backend.core.config import settings

engine = make_engine(settings.database_url)
SessionFactory = make_session_factory(engine)

async def get_session() -> AsyncSession:
    async with SessionFactory() as session:
        yield session
```

- [ ] **Step 4: 寫失敗的測試**

建立 `src/backend/tests/conftest.py`：

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.core.database import Base, get_session, make_engine, make_session_factory
from src.backend.core.config import settings

TEST_URL = settings.test_database_url or "postgresql+asyncpg://vsuser:vspass@localhost:5433/verbal_sparring_test"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    eng = make_engine(TEST_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()

@pytest_asyncio.fixture
async def db(test_engine):
    factory = make_session_factory(test_engine)
    async with factory() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db: AsyncSession):
    from src.backend.main import app
    app.dependency_overrides[get_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

建立 `src/backend/tests/test_health.py`（先寫測試，此時 main.py 還不存在）：

```python
import pytest

async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 5: 執行確認失敗**

```bash
cd src/backend && pytest tests/test_health.py -v
```

Expected: `ModuleNotFoundError` 或 `ImportError`（main.py 尚不存在）

- [ ] **Step 6: 建立 `src/backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="唇槍舌戰 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: 執行確認通過**

```bash
cd src/backend && pytest tests/test_health.py -v
```

Expected: `PASSED`

- [ ] **Step 8: Commit**

```bash
git add src/backend/core/ src/backend/main.py src/backend/tests/ src/backend/pytest.ini
git commit -m "feat: backend foundation — config, database, FastAPI app, health endpoint"
```

---

## Task 3: 資料庫 Models + Alembic

**Files:**
- Create: `src/backend/models/player.py`
- Create: `src/backend/models/match.py`
- Create: `src/backend/models/game_round.py`
- Create: `src/backend/models/npc_memory.py`
- Create: `src/backend/models/__init__.py`
- Create: `src/backend/alembic.ini`
- Create: `src/backend/alembic/env.py`

- [ ] **Step 1: 建立 `src/backend/models/player.py`**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.backend.core.database import Base

class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_damage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: 建立 `src/backend/models/match.py`**

```python
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.backend.core.database import Base

class MatchStatus(str, enum.Enum):
    pending = "pending"
    ongoing = "ongoing"
    finished = "finished"

class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player1_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    player2_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    winner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    status: Mapped[MatchStatus] = mapped_column(SAEnum(MatchStatus), default=MatchStatus.pending, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 3: 建立 `src/backend/models/game_round.py`**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.backend.core.database import Base

class GameRound(Base):
    __tablename__ = "rounds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attacker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_text: Mapped[str] = mapped_column(Text, nullable=False)
    damage: Mapped[int] = mapped_column(Integer, nullable=False)
    referee_comment: Mapped[str] = mapped_column(Text, nullable=False)
    hp_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: 建立 `src/backend/models/npc_memory.py`**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.backend.core.database import Base

class NpcMemory(Base):
    __tablename__ = "npc_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opponent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), unique=True, nullable=False)
    attack_patterns: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    weaknesses: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    avg_damage_recv: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    round_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 5: 建立 `src/backend/models/__init__.py`**

```python
from src.backend.models.player import Player
from src.backend.models.match import Match, MatchStatus
from src.backend.models.game_round import GameRound
from src.backend.models.npc_memory import NpcMemory

__all__ = ["Player", "Match", "MatchStatus", "GameRound", "NpcMemory"]
```

- [ ] **Step 6: 寫失敗的 model 測試**

建立 `src/backend/tests/test_models.py`：

```python
import pytest
from sqlalchemy import select
from src.backend.models import Player, Match, MatchStatus, GameRound, NpcMemory

async def test_create_player(db):
    player = Player(username="tester", password_hash="hash")
    db.add(player)
    await db.commit()
    result = await db.execute(select(Player).where(Player.username == "tester"))
    p = result.scalar_one()
    assert p.wins == 0
    assert p.total_damage == 0

async def test_create_match(db):
    match = Match(status=MatchStatus.ongoing)
    db.add(match)
    await db.commit()
    result = await db.execute(select(Match).where(Match.status == MatchStatus.ongoing))
    m = result.scalar_one()
    assert m.player1_id is None  # NPC match

async def test_create_game_round(db):
    match = Match()
    db.add(match)
    await db.flush()
    rnd = GameRound(
        match_id=match.id,
        round_number=1,
        display_text="你好遜！",
        damage=20,
        referee_comment="有點東西",
        hp_snapshot={"Player_1": 80, "Player_2": 100},
    )
    db.add(rnd)
    await db.commit()
    result = await db.execute(select(GameRound).where(GameRound.match_id == match.id))
    r = result.scalar_one()
    assert r.damage == 20
    assert r.hp_snapshot["Player_1"] == 80
```

- [ ] **Step 7: 執行確認失敗（tables 尚未 create）**

```bash
cd src/backend && pytest tests/test_models.py -v
```

Expected: 錯誤（表不存在）。`conftest.py` 中的 `test_engine` fixture 會呼叫 `Base.metadata.create_all`，但 models 尚未匯入進 `Base`。

- [ ] **Step 8: 在 `database.py` 底部確保 models import**

在 `src/backend/core/database.py` 的最後加：

```python
# 確保所有 model 都被匯入讓 Base.metadata 知道它們
def _import_models():
    from src.backend.models import Player, Match, GameRound, NpcMemory  # noqa: F401
```

在 `conftest.py` 的 `test_engine` fixture 中，在 `create_all` 前加一行：

```python
from src.backend.core.database import _import_models
_import_models()
```

完整更新後的 `test_engine` fixture：

```python
@pytest_asyncio.fixture(scope="session")
async def test_engine():
    from src.backend.core.database import _import_models
    _import_models()
    eng = make_engine(TEST_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()
```

- [ ] **Step 9: 執行確認通過**

```bash
cd src/backend && pytest tests/test_models.py -v
```

Expected: 3 個 `PASSED`

- [ ] **Step 10: 設定 Alembic（供正式環境 migration 用）**

```bash
cd src/backend && alembic init alembic
```

編輯 `src/backend/alembic/env.py`，找到 `target_metadata = None` 那行，換成：

```python
from src.backend.core.database import Base, _import_models
_import_models()
target_metadata = Base.metadata
```

同時在 `alembic/env.py` 的 `run_migrations_online` 函式中，將 `connectable` 的設定改為讀取環境變數：

```python
from src.backend.core.config import settings
# 在 run_migrations_online() 內：
connectable = create_engine(settings.database_url.replace("+asyncpg", ""))
```

在 `alembic.ini` 中將 `sqlalchemy.url` 一行改為：

```ini
sqlalchemy.url = %(DATABASE_URL)s
```

- [ ] **Step 11: 產生並套用 migration（正式 DB）**

```bash
cd src/backend && alembic revision --autogenerate -m "init tables"
alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade  -> <hash>, init tables`

- [ ] **Step 12: Commit**

```bash
git add src/backend/models/ src/backend/alembic/ src/backend/alembic.ini src/backend/core/ src/backend/tests/
git commit -m "feat: database models (Player, Match, GameRound, NpcMemory) + Alembic migrations"
```

---

## Task 4: Auth 服務 + API（register / login / JWT）

**Files:**
- Create: `src/backend/services/auth.py`
- Create: `src/backend/schemas/auth.py`
- Create: `src/backend/api/routes/auth.py`
- Modify: `src/backend/main.py`
- Create: `src/backend/tests/test_auth.py`

- [ ] **Step 1: 建立 `src/backend/services/auth.py`**

```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from src.backend.core.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "username": username, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return {}
```

- [ ] **Step 2: 建立 `src/backend/schemas/auth.py`**

```python
from pydantic import BaseModel

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: str
```

- [ ] **Step 3: 建立 `src/backend/api/routes/auth.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.backend.core.database import get_session
from src.backend.models import Player
from src.backend.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from src.backend.services.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_session)):
    existing = await db.execute(select(Player).where(Player.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")
    player = Player(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )
    db.add(player)
    await db.commit()
    token = create_access_token(str(player.id), player.username)
    return TokenResponse(access_token=token, username=player.username, user_id=str(player.id))

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Player).where(Player.username == req.username))
    player = result.scalar_one_or_none()
    if not player or not verify_password(req.password, player.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(player.id), player.username)
    return TokenResponse(access_token=token, username=player.username, user_id=str(player.id))
```

- [ ] **Step 4: 在 `main.py` 掛載 router**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.backend.api.routes.auth import router as auth_router

app = FastAPI(title="唇槍舌戰 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 寫失敗的 auth 測試**

建立 `src/backend/tests/test_auth.py`：

```python
import pytest

async def test_register_success(client):
    resp = await client.post("/api/auth/register", json={"username": "alice", "password": "pw123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert "access_token" in data

async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={"username": "bob", "password": "pw"})
    resp = await client.post("/api/auth/register", json={"username": "bob", "password": "pw"})
    assert resp.status_code == 409

async def test_login_success(client):
    await client.post("/api/auth/register", json={"username": "carol", "password": "secret"})
    resp = await client.post("/api/auth/login", json={"username": "carol", "password": "secret"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={"username": "dan", "password": "right"})
    resp = await client.post("/api/auth/login", json={"username": "dan", "password": "wrong"})
    assert resp.status_code == 401
```

- [ ] **Step 6: 執行確認失敗**

```bash
cd src/backend && pytest tests/test_auth.py -v
```

Expected: ImportError 或路由 404（router 未掛載時）

- [ ] **Step 7: 執行確認通過**

確認 main.py 已 include router 後：

```bash
cd src/backend && pytest tests/test_auth.py -v
```

Expected: 4 個 `PASSED`

- [ ] **Step 8: Commit**

```bash
git add src/backend/services/auth.py src/backend/schemas/auth.py src/backend/api/routes/auth.py src/backend/main.py src/backend/tests/test_auth.py
git commit -m "feat: auth service — register, login, JWT"
```

---

## Task 5: Matches REST API（建立對局、查詢當前對局）

**Files:**
- Create: `src/backend/schemas/match.py`
- Create: `src/backend/api/routes/matches.py`
- Modify: `src/backend/main.py`
- Create: `src/backend/tests/test_matches.py`

- [ ] **Step 1: 建立 `src/backend/schemas/match.py`**

```python
from pydantic import BaseModel
from uuid import UUID

class CreateMatchRequest(BaseModel):
    opponent: str  # "npc" 或對手的 username

class MatchResponse(BaseModel):
    match_id: str
    opponent: str
    is_npc: bool
```

- [ ] **Step 2: 建立 auth 依賴函式（供各 route 共用）**

在 `src/backend/services/auth.py` 末尾加：

```python
from fastapi import HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_current_player(authorization: str = Header(...), db: AsyncSession = None):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload  # {"sub": user_id, "username": username}
```

- [ ] **Step 3: 建立 `src/backend/api/routes/matches.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.backend.core.database import get_session
from src.backend.models import Match, MatchStatus, Player
from src.backend.schemas.match import CreateMatchRequest, MatchResponse
from src.backend.services.auth import get_current_player

router = APIRouter(prefix="/api/matches", tags=["matches"])

@router.post("", response_model=MatchResponse, status_code=201)
async def create_match(
    req: CreateMatchRequest,
    db: AsyncSession = Depends(get_session),
    current: dict = Depends(get_current_player),
):
    is_npc = req.opponent.lower() == "npc"
    player2_id = None

    if not is_npc:
        result = await db.execute(select(Player).where(Player.username == req.opponent))
        opponent = result.scalar_one_or_none()
        if not opponent:
            raise HTTPException(status_code=404, detail="Opponent not found")
        player2_id = opponent.id

    match = Match(
        player1_id=current["sub"],
        player2_id=player2_id,
        status=MatchStatus.pending,
    )
    db.add(match)
    await db.commit()
    return MatchResponse(
        match_id=str(match.id),
        opponent=req.opponent,
        is_npc=is_npc,
    )
```

- [ ] **Step 4: 在 `main.py` 掛載 router**

```python
from src.backend.api.routes.matches import router as matches_router
# 在 app.include_router(auth_router) 之後加：
app.include_router(matches_router)
```

- [ ] **Step 5: 寫失敗的 matches 測試**

建立 `src/backend/tests/test_matches.py`：

```python
import pytest

async def _register_and_token(client, username="player1"):
    resp = await client.post("/api/auth/register", json={"username": username, "password": "pw"})
    return resp.json()["access_token"]

async def test_create_npc_match(client):
    token = await _register_and_token(client, "alice2")
    resp = await client.post(
        "/api/matches",
        json={"opponent": "npc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_npc"] is True
    assert "match_id" in data

async def test_create_match_opponent_not_found(client):
    token = await _register_and_token(client, "bob2")
    resp = await client.post(
        "/api/matches",
        json={"opponent": "nonexistent"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

async def test_create_match_vs_human(client):
    t1 = await _register_and_token(client, "player_a")
    await client.post("/api/auth/register", json={"username": "player_b", "password": "pw"})
    resp = await client.post(
        "/api/matches",
        json={"opponent": "player_b"},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_npc"] is False
```

- [ ] **Step 6: 執行確認通過**

```bash
cd src/backend && pytest tests/test_matches.py -v
```

Expected: 3 個 `PASSED`

- [ ] **Step 7: Commit**

```bash
git add src/backend/schemas/match.py src/backend/api/routes/matches.py src/backend/main.py src/backend/tests/test_matches.py src/backend/services/auth.py
git commit -m "feat: matches REST API — create match vs NPC or human player"
```

---

## Task 6: LangGraph 裁判 Graph

**Files:**
- Create: `src/backend/services/referee/graph.py`
- Create: `src/backend/tests/test_referee.py`

- [ ] **Step 1: 寫失敗的 referee 測試**

建立 `src/backend/tests/test_referee.py`：

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.backend.services.referee.graph import run_referee

MOCK_OLLAMA_RESPONSE = '{"damage": 22, "referee_comment": "嘴砲有力", "display_text": "你這廢物！"}'

async def test_referee_returns_valid_result():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = MOCK_OLLAMA_RESPONSE
        result = await run_referee("你好遜", None)
    assert result["damage"] == 22
    assert result["comment"] == "嘴砲有力"
    assert result["display_text"] == "你這廢物！"

async def test_referee_clamps_damage():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = '{"damage": 99, "referee_comment": "爆表", "display_text": "X"}'
        result = await run_referee("超強攻擊", None)
    assert result["damage"] == 30  # clamped to max

async def test_referee_handles_parse_failure():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "我不知道啊"
        result = await run_referee("測試", None)
    assert result["damage"] == 10
    assert "裁判嘴瓢" in result["comment"]
```

- [ ] **Step 2: 執行確認失敗**

```bash
cd src/backend && pytest tests/test_referee.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: 建立 `src/backend/services/referee/graph.py`**

```python
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.backend.core.config import settings

class RefereeState(TypedDict):
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
    ("我要把你打到媽都不認得", '{"damage": 26, "referee_comment": "幼兒園嘴砲等級", "display_text": "你這廢物，連出生都是錯誤！"}'),
    ("早安，今天天氣真好", '{"damage": 11, "referee_comment": "場子被你拖到零下了", "display_text": "你的存在本身就是在浪費空氣！"}'),
]


async def _call_ollama(messages: list[dict]) -> str:
    import httpx
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
    msgs = [{"role": "user", "content": f"{_SYSTEM_PROMPT}\n\n玩家發言：「{_FEW_SHOT[0][0]}」"}]
    msgs.append({"role": "assistant", "content": _FEW_SHOT[0][1]})
    for player_text, json_out in _FEW_SHOT[1:]:
        msgs.append({"role": "user", "content": f"玩家發言：「{player_text}」"})
        msgs.append({"role": "assistant", "content": json_out})

    if image_b64:
        instruction = f"玩家丟出圖嗆對手，附帶：「{text}」。認出圖裡的東西後毒舌評分。" if text else "玩家丟出圖嗆對手。認出圖裡的東西後毒舌評分。"
        content = [{"type": "image_url", "image_url": {"url": image_b64}}, {"type": "text", "text": instruction}]
    else:
        content = f"玩家發言：「{text}」"
    msgs.append({"role": "user", "content": content})
    return msgs


def _extract_json(text: str) -> dict | None:
    for candidate in (text.strip(), text.strip().replace("```json", "").replace("```", "").strip()):
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
                    obj = json.loads(text[start:i + 1])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    pass
                start = -1
    return None


async def _node_call_ollama(state: RefereeState) -> RefereeState:
    msgs = _build_messages(state["original_text"], state.get("image_b64"))
    state["raw_response"] = await _call_ollama(msgs)
    return state


def _node_parse_response(state: RefereeState) -> RefereeState:
    parsed = _extract_json(state["raw_response"])
    if parsed is None:
        state["damage"] = 10
        state["comment"] = "裁判嘴瓢了"
        state["display_text"] = state["original_text"] or "（無言以對）"
    else:
        state["damage"] = int(parsed.get("damage", 15))
        state["comment"] = str(parsed.get("referee_comment", "裁判已介入"))
        state["display_text"] = str(parsed.get("display_text", state["original_text"] or ""))
    return state


def _node_validate_clamp(state: RefereeState) -> RefereeState:
    state["damage"] = max(10, min(30, state["damage"]))
    state["comment"] = state["comment"][:40]
    return state


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
    initial: RefereeState = {
        "original_text": text,
        "image_b64": image_b64,
        "raw_response": "",
        "damage": 10,
        "comment": "",
        "display_text": "",
    }
    result = await _referee_graph.ainvoke(initial)
    return {"damage": result["damage"], "comment": result["comment"], "display_text": result["display_text"]}
```

- [ ] **Step 4: 執行確認通過**

```bash
cd src/backend && pytest tests/test_referee.py -v
```

Expected: 3 個 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/backend/services/referee/graph.py src/backend/tests/test_referee.py
git commit -m "feat: LangGraph referee graph — single Ollama call + Python parse/clamp nodes"
```

---

## Task 7: LangGraph NPC Agent

**Files:**
- Create: `src/backend/services/npc/agent.py`
- Create: `src/backend/tests/test_npc.py`

- [ ] **Step 1: 寫失敗的 NPC 測試**

建立 `src/backend/tests/test_npc.py`：

```python
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from src.backend.services.npc.agent import run_npc_turn

MOCK_NPC_RESPONSE = "你的攻擊力跟你的智商一樣低！"

async def test_npc_generates_attack(db):
    opponent_id = str(uuid.uuid4())
    with patch("src.backend.services.npc.agent._call_ollama", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_NPC_RESPONSE
        result = await run_npc_turn(
            db=db,
            match_id=str(uuid.uuid4()),
            opponent_id=opponent_id,
            my_hp=100,
            opponent_hp=80,
            round_number=1,
            recent_opponent_attacks=["你好遜"],
        )
    assert isinstance(result, str)
    assert len(result) > 0

async def test_npc_uses_memory_in_prompt(db):
    opponent_id = str(uuid.uuid4())
    # 先建立記憶
    from src.backend.models import NpcMemory, Player
    player = Player(id=uuid.UUID(opponent_id), username=f"u_{opponent_id[:6]}", password_hash="x")
    db.add(player)
    memory = NpcMemory(
        opponent_id=uuid.UUID(opponent_id),
        attack_patterns=["愛用圖攻擊"],
        weaknesses=["怕文字嗆"],
        round_count=3,
    )
    db.add(memory)
    await db.commit()

    captured_prompt = []
    async def capture_call(messages):
        captured_prompt.extend(messages)
        return "記憶驅動攻擊！"

    with patch("src.backend.services.npc.agent._call_ollama", side_effect=capture_call):
        await run_npc_turn(
            db=db,
            match_id=str(uuid.uuid4()),
            opponent_id=opponent_id,
            my_hp=60,
            opponent_hp=100,
            round_number=5,
            recent_opponent_attacks=["圖攻擊1", "圖攻擊2"],
        )
    full_prompt = str(captured_prompt)
    assert "愛用圖攻擊" in full_prompt
```

- [ ] **Step 2: 執行確認失敗**

```bash
cd src/backend && pytest tests/test_npc.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: 建立 `src/backend/services/npc/agent.py`**

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.backend.models import NpcMemory
from src.backend.core.config import settings
import httpx


class NPCState(TypedDict):
    match_id: str
    opponent_id: str
    my_hp: int
    opponent_hp: int
    round_number: int
    recent_opponent_attacks: list[str]
    memory: dict
    attack_text: str


async def _call_ollama(messages: list[dict]) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.9},
    }
    async with httpx.AsyncClient(timeout=60) as c:
        resp = await c.post(f"{settings.ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()


_NPC_SYSTEM = (
    "你是一個毒舌 AI 格鬥選手。根據戰況與對手記憶，生成一句 20 字內的嗆聲攻擊（繁體中文）。"
    "直接輸出攻擊文字，不加任何說明。"
)


def _build_npc_messages(state: NPCState) -> list[dict]:
    mem = state["memory"]
    memory_summary = ""
    if mem.get("round_count", 0) > 0:
        patterns = "、".join(mem.get("attack_patterns", [])[:3]) or "無特殊模式"
        weaknesses = "、".join(mem.get("weaknesses", [])[:3]) or "未知弱點"
        memory_summary = f"\n對手習慣：{patterns}\n對手弱點：{weaknesses}\n歷史場數：{mem['round_count']}"

    recent = "、".join(state["recent_opponent_attacks"][-3:]) or "無"
    situation = (
        f"當前戰況：我方HP {state['my_hp']} vs 對手HP {state['opponent_hp']}，"
        f"第 {state['round_number']} 回合。"
        f"對手最近攻擊：「{recent}」。"
        f"{memory_summary}"
    )
    return [
        {"role": "user", "content": f"{_NPC_SYSTEM}\n\n{situation}\n\n生成你這回合的攻擊："},
    ]


async def _node_call_ollama(state: NPCState) -> NPCState:
    msgs = _build_npc_messages(state)
    state["attack_text"] = await _call_ollama(msgs)
    return state


_graph = StateGraph(NPCState)
_graph.add_node("call_ollama", _node_call_ollama)
_graph.set_entry_point("call_ollama")
_graph.add_edge("call_ollama", END)
_npc_graph = _graph.compile()


async def _get_memory(db: AsyncSession, opponent_id: str) -> dict:
    result = await db.execute(select(NpcMemory).where(NpcMemory.opponent_id == opponent_id))
    mem = result.scalar_one_or_none()
    if not mem:
        return {}
    return {
        "attack_patterns": mem.attack_patterns,
        "weaknesses": mem.weaknesses,
        "avg_damage_recv": mem.avg_damage_recv,
        "round_count": mem.round_count,
    }


async def update_npc_memory(
    db: AsyncSession,
    opponent_id: str,
    new_pattern: str | None,
    damage_received: int,
):
    from uuid import UUID
    result = await db.execute(select(NpcMemory).where(NpcMemory.opponent_id == UUID(opponent_id)))
    mem = result.scalar_one_or_none()
    if not mem:
        mem = NpcMemory(opponent_id=UUID(opponent_id))
        db.add(mem)
    if new_pattern and new_pattern not in mem.attack_patterns:
        mem.attack_patterns = [*mem.attack_patterns, new_pattern][-10:]
    total = mem.avg_damage_recv * mem.round_count + damage_received
    mem.round_count += 1
    mem.avg_damage_recv = total / mem.round_count
    await db.commit()


async def run_npc_turn(
    db: AsyncSession,
    match_id: str,
    opponent_id: str,
    my_hp: int,
    opponent_hp: int,
    round_number: int,
    recent_opponent_attacks: list[str],
) -> str:
    memory = await _get_memory(db, opponent_id)
    initial: NPCState = {
        "match_id": match_id,
        "opponent_id": opponent_id,
        "my_hp": my_hp,
        "opponent_hp": opponent_hp,
        "round_number": round_number,
        "recent_opponent_attacks": recent_opponent_attacks,
        "memory": memory,
        "attack_text": "",
    }
    result = await _npc_graph.ainvoke(initial)
    return result["attack_text"]
```

- [ ] **Step 4: 執行確認通過**

```bash
cd src/backend && pytest tests/test_npc.py -v
```

Expected: 2 個 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/backend/services/npc/agent.py src/backend/tests/test_npc.py
git commit -m "feat: LangGraph NPC agent — ReAct with PostgreSQL opponent memory"
```

---

## Task 8: GameRoom 服務 + WebSocket 對戰 Endpoint

**Files:**
- Create: `src/backend/services/game/room.py`
- Create: `src/backend/api/ws/battle_ws.py`
- Modify: `src/backend/main.py`
- Create: `src/backend/tests/test_game_room.py`
- Create: `src/backend/tests/test_websocket.py`

- [ ] **Step 1: 建立 `src/backend/services/game/room.py`**

```python
from dataclasses import dataclass, field
from fastapi import WebSocket

@dataclass
class GameRoom:
    match_id: str
    is_npc: bool = False
    connections: dict[str, WebSocket] = field(default_factory=dict)
    hp: dict[str, int] = field(default_factory=lambda: {})
    current_turn: str = ""
    round_number: int = 0
    recent_attacks: list[str] = field(default_factory=list)  # 最近 3 次真人攻擊（供 NPC 記憶用）

    def connect(self, player_id: str, ws: WebSocket):
        self.connections[player_id] = ws
        if player_id not in self.hp:
            self.hp[player_id] = 100

    def disconnect(self, player_id: str):
        self.connections.pop(player_id, None)

    async def broadcast(self, message: dict):
        import json
        for ws in self.connections.values():
            await ws.send_text(json.dumps(message, ensure_ascii=False))

    async def send_to(self, player_id: str, message: dict):
        import json
        ws = self.connections.get(player_id)
        if ws:
            await ws.send_text(json.dumps(message, ensure_ascii=False))

    def is_full(self) -> bool:
        if self.is_npc:
            return len(self.connections) >= 1
        return len(self.connections) >= 2

    def record_attack(self, text: str):
        self.recent_attacks = [*self.recent_attacks, text][-3:]

    def reset(self):
        self.hp = {p: 100 for p in self.connections}
        self.current_turn = sorted(self.connections.keys())[0]
        self.round_number = 0
        self.recent_attacks = []


# 全域 rooms dict（進程內多房間支援）
rooms: dict[str, GameRoom] = {}
```

- [ ] **Step 2: 寫失敗的 GameRoom 單元測試**

建立 `src/backend/tests/test_game_room.py`：

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.services.game.room import GameRoom

def test_connect_sets_hp():
    room = GameRoom(match_id="test-match")
    ws = MagicMock()
    room.connect("alice", ws)
    assert room.hp["alice"] == 100

def test_is_full_npc():
    room = GameRoom(match_id="npc-match", is_npc=True)
    ws = MagicMock()
    room.connect("alice", ws)
    assert room.is_full() is True

def test_is_full_human_vs_human():
    room = GameRoom(match_id="pvp-match", is_npc=False)
    ws1, ws2 = MagicMock(), MagicMock()
    room.connect("alice", ws1)
    assert room.is_full() is False
    room.connect("bob", ws2)
    assert room.is_full() is True

def test_record_attack_keeps_last_3():
    room = GameRoom(match_id="m")
    for i in range(5):
        room.record_attack(f"attack{i}")
    assert room.recent_attacks == ["attack2", "attack3", "attack4"]

def test_reset_restores_hp():
    room = GameRoom(match_id="m")
    room.connect("alice", MagicMock())
    room.hp["alice"] = 30
    room.reset()
    assert room.hp["alice"] == 100
```

- [ ] **Step 3: 執行確認通過**

```bash
cd src/backend && pytest tests/test_game_room.py -v
```

Expected: 5 個 `PASSED`

- [ ] **Step 4: 建立 `src/backend/api/ws/battle_ws.py`**

```python
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.backend.core.database import get_session
from src.backend.models import Match, MatchStatus, GameRound, Player
from src.backend.services.game.room import GameRoom, rooms
from src.backend.services.referee.graph import run_referee
from src.backend.services.npc.agent import run_npc_turn, update_npc_memory
from src.backend.services.auth import decode_token
import uuid
from datetime import datetime, timezone

router = APIRouter()


async def _persist_round(
    db: AsyncSession,
    match_id: str,
    round_number: int,
    attacker_id: str | None,
    original_text: str,
    image_b64: str | None,
    display_text: str,
    damage: int,
    referee_comment: str,
    hp_snapshot: dict,
):
    rnd = GameRound(
        match_id=uuid.UUID(match_id),
        round_number=round_number,
        attacker_id=uuid.UUID(attacker_id) if attacker_id else None,
        original_text=original_text,
        image_b64=image_b64,
        display_text=display_text,
        damage=damage,
        referee_comment=referee_comment,
        hp_snapshot=hp_snapshot,
    )
    db.add(rnd)
    await db.commit()


async def _finish_match(db: AsyncSession, match_id: str, winner_id: str | None):
    result = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
    match = result.scalar_one_or_none()
    if match:
        match.status = MatchStatus.finished
        match.winner_id = uuid.UUID(winner_id) if winner_id else None
        match.ended_at = datetime.now(timezone.utc)
        await db.commit()

    if winner_id:
        result = await db.execute(select(Player).where(Player.id == uuid.UUID(winner_id)))
        winner = result.scalar_one_or_none()
        if winner:
            winner.wins += 1
            await db.commit()


@router.websocket("/ws/battle/{match_id}/{player_id}")
async def battle_ws(
    websocket: WebSocket,
    match_id: str,
    player_id: str,
    token: str = "",
    db: AsyncSession = Depends(get_session),
):
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    result = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
    match = result.scalar_one_or_none()
    if not match:
        await websocket.send_text(json.dumps({"type": "error", "message": "Match not found"}))
        await websocket.close()
        return

    is_npc = match.player2_id is None
    if match_id not in rooms:
        rooms[match_id] = GameRoom(match_id=match_id, is_npc=is_npc)

    room = rooms[match_id]
    room.connect(player_id, websocket)
    if is_npc and "NPC" not in room.hp:
        room.hp["NPC"] = 100  # NPC 不連 WebSocket，手動初始化 HP

    if not room.current_turn:
        room.current_turn = player_id

    if match.status == MatchStatus.pending:
        if (is_npc and room.is_full()) or (not is_npc and room.is_full()):
            match.status = MatchStatus.ongoing
            match.started_at = datetime.now(timezone.utc)
            await db.commit()

    await room.broadcast({
        "type": "system",
        "message": f"【{player_id}】進入競技場！",
        "hp_status": room.hp,
        "current_turn": room.current_turn,
    })

    opponent_id = str(match.player1_id) if payload["sub"] != str(match.player1_id) else str(match.player2_id or "")

    try:
        while True:
            raw = await websocket.receive_text()
            payload_data = json.loads(raw)
            text = payload_data.get("text", "")
            image_b64 = payload_data.get("image")

            if player_id != room.current_turn:
                await room.send_to(player_id, {
                    "type": "turn_error",
                    "message": "還沒輪到你！",
                    "hp_status": room.hp,
                    "current_turn": room.current_turn,
                })
                continue

            if not text and not image_b64:
                continue

            room.round_number += 1
            room.record_attack(text or "（圖片）")

            ref = await run_referee(text, image_b64)
            damage, comment, display_text = ref["damage"], ref["comment"], ref["display_text"]

            target = "NPC" if is_npc else [p for p in room.hp if p != player_id][0]
            room.hp[target] = max(0, room.hp[target] - damage)

            attacker_player_id = payload["sub"]
            await _persist_round(
                db, match_id, room.round_number, attacker_player_id,
                text, image_b64, display_text, damage, comment, dict(room.hp),
            )

            result = await db.execute(select(Player).where(Player.id == uuid.UUID(attacker_player_id)))
            attacker = result.scalar_one_or_none()
            if attacker:
                attacker.total_damage += damage
                await db.commit()

            room.current_turn = target
            await room.broadcast({
                "type": "attack",
                "sender": player_id,
                "display_text": display_text,
                "damage": damage,
                "referee_comment": comment,
                "hp_status": dict(room.hp),
                "current_turn": room.current_turn,
            })

            if room.hp[target] <= 0:
                await _finish_match(db, match_id, attacker_player_id)
                await room.broadcast({
                    "type": "game_over",
                    "message": f"【{player_id}】把對手噴到生活不能自理！",
                    "winner": player_id,
                })
                room.reset()
                await room.broadcast({
                    "type": "system",
                    "message": "新的一局開始！",
                    "hp_status": room.hp,
                    "current_turn": room.current_turn,
                })
                continue

            if is_npc and room.current_turn != player_id:
                npc_text = await run_npc_turn(
                    db=db,
                    match_id=match_id,
                    opponent_id=attacker_player_id,
                    my_hp=room.hp.get("NPC", 100),
                    opponent_hp=room.hp.get(player_id, 100),
                    round_number=room.round_number,
                    recent_opponent_attacks=room.recent_attacks,
                )
                npc_ref = await run_referee(npc_text, None)
                room.hp[player_id] = max(0, room.hp.get(player_id, 100) - npc_ref["damage"])
                room.round_number += 1

                await _persist_round(
                    db, match_id, room.round_number, None,
                    npc_text, None, npc_ref["display_text"],
                    npc_ref["damage"], npc_ref["comment"], dict(room.hp),
                )

                room.current_turn = player_id
                await room.broadcast({
                    "type": "npc_attack",
                    "display_text": npc_ref["display_text"],
                    "damage": npc_ref["damage"],
                    "referee_comment": npc_ref["comment"],
                    "hp_status": dict(room.hp),
                })

                if room.hp.get(player_id, 100) <= 0:
                    asyncio.create_task(
                        update_npc_memory(db, attacker_player_id, room.recent_attacks[-1] if room.recent_attacks else None, npc_ref["damage"])
                    )
                    await _finish_match(db, match_id, None)
                    await room.broadcast({"type": "game_over", "message": "AI 裁判：就這點實力？", "winner": "NPC"})
                    room.reset()

    except WebSocketDisconnect:
        room.disconnect(player_id)
        if not room.connections:
            rooms.pop(match_id, None)
        else:
            await room.broadcast({
                "type": "system",
                "message": f"【{player_id}】承受不住壓力逃跑了！",
                "hp_status": room.hp,
                "current_turn": room.current_turn,
            })
```

- [ ] **Step 5: 在 `main.py` 掛載 WebSocket router**

```python
from src.backend.api.ws.battle_ws import router as ws_router
# 在已有的 include_router 之後加：
app.include_router(ws_router)
```

- [ ] **Step 6: 寫 WebSocket 整合測試**

建立 `src/backend/tests/test_websocket.py`：

```python
import pytest
import json
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient
from src.backend.main import app

def _setup_player_and_match(client, username="ws_player"):
    reg = client.post("/api/auth/register", json={"username": username, "password": "pw"})
    token = reg.json()["access_token"]
    match = client.post(
        "/api/matches",
        json={"opponent": "npc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, match.json()["match_id"]

def test_websocket_connect_and_system_message():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_ref, \
         patch("src.backend.services.npc.agent._call_ollama", new_callable=AsyncMock) as mock_npc:
        mock_ref.return_value = '{"damage": 15, "referee_comment": "不錯", "display_text": "你很差！"}'
        mock_npc.return_value = "你的臉跟你的攻擊一樣難看"

        with TestClient(app) as client:
            token, match_id = _setup_player_and_match(client, "ws_tester")
            with client.websocket_connect(f"/ws/battle/{match_id}/ws_tester?token={token}") as ws:
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "system"
                assert "ws_tester" in msg["message"]

def test_websocket_attack_reduces_hp():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_ref, \
         patch("src.backend.services.npc.agent._call_ollama", new_callable=AsyncMock) as mock_npc:
        mock_ref.return_value = '{"damage": 20, "referee_comment": "猛", "display_text": "超猛攻擊！"}'
        mock_npc.return_value = "廢物"

        with TestClient(app) as client:
            token, match_id = _setup_player_and_match(client, "ws_attacker")
            with client.websocket_connect(f"/ws/battle/{match_id}/ws_attacker?token={token}") as ws:
                ws.receive_text()  # system
                ws.send_text(json.dumps({"text": "你好遜"}))
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "attack"
                assert msg["damage"] == 20
```

- [ ] **Step 7: 執行確認通過**

```bash
cd src/backend && pytest tests/test_game_room.py tests/test_websocket.py -v
```

Expected: 7 個 `PASSED`

- [ ] **Step 8: Commit**

```bash
git add src/backend/services/game/ src/backend/api/ws/ src/backend/main.py src/backend/tests/test_game_room.py src/backend/tests/test_websocket.py
git commit -m "feat: GameRoom service + WebSocket battle endpoint with NPC auto-response"
```

---

## Task 9: Leaderboard + Replay REST APIs

**Files:**
- Create: `src/backend/schemas/leaderboard.py`
- Create: `src/backend/schemas/replay.py`
- Create: `src/backend/api/routes/leaderboard.py`
- Create: `src/backend/api/routes/replay.py`
- Modify: `src/backend/main.py`
- Create: `src/backend/tests/test_api.py`

- [ ] **Step 1: 建立 `src/backend/schemas/leaderboard.py`**

```python
from pydantic import BaseModel

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_damage: int
    wins: int
    losses: int

class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
```

- [ ] **Step 2: 建立 `src/backend/schemas/replay.py`**

```python
from pydantic import BaseModel
from uuid import UUID

class RoundSnapshot(BaseModel):
    round_number: int
    attacker: str | None  # username 或 "NPC"
    original_text: str | None
    display_text: str
    damage: int
    referee_comment: str
    hp_snapshot: dict

class ReplayResponse(BaseModel):
    match_id: str
    rounds: list[RoundSnapshot]
```

- [ ] **Step 3: 建立 `src/backend/api/routes/leaderboard.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.backend.core.database import get_session
from src.backend.models import Player
from src.backend.schemas.leaderboard import LeaderboardResponse, LeaderboardEntry

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Player).order_by(desc(Player.total_damage)).limit(50)
    )
    players = result.scalars().all()
    entries = [
        LeaderboardEntry(
            rank=i + 1,
            username=p.username,
            total_damage=p.total_damage,
            wins=p.wins,
            losses=p.losses,
        )
        for i, p in enumerate(players)
    ]
    return LeaderboardResponse(entries=entries)
```

- [ ] **Step 4: 建立 `src/backend/api/routes/replay.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.backend.core.database import get_session
from src.backend.models import Match, GameRound, Player
from src.backend.schemas.replay import ReplayResponse, RoundSnapshot
import uuid

router = APIRouter(prefix="/api/replay", tags=["replay"])

@router.get("/{match_id}", response_model=ReplayResponse)
async def get_replay(match_id: str, db: AsyncSession = Depends(get_session)):
    try:
        mid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid match_id")

    match = await db.execute(select(Match).where(Match.id == mid))
    if not match.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Match not found")

    rounds_result = await db.execute(
        select(GameRound).where(GameRound.match_id == mid).order_by(GameRound.round_number)
    )
    rounds = rounds_result.scalars().all()

    snapshots = []
    for r in rounds:
        attacker_name = "NPC"
        if r.attacker_id:
            p = await db.execute(select(Player).where(Player.id == r.attacker_id))
            player = p.scalar_one_or_none()
            attacker_name = player.username if player else "Unknown"
        snapshots.append(RoundSnapshot(
            round_number=r.round_number,
            attacker=attacker_name,
            original_text=r.original_text,
            display_text=r.display_text,
            damage=r.damage,
            referee_comment=r.referee_comment,
            hp_snapshot=r.hp_snapshot,
        ))

    return ReplayResponse(match_id=match_id, rounds=snapshots)
```

- [ ] **Step 5: 在 `main.py` 掛載兩個 router**

```python
from src.backend.api.routes.leaderboard import router as leaderboard_router
from src.backend.api.routes.replay import router as replay_router
app.include_router(leaderboard_router)
app.include_router(replay_router)
```

- [ ] **Step 6: 寫失敗的 API 測試**

建立 `src/backend/tests/test_api.py`：

```python
import pytest
import uuid

async def _setup(client, username="lb_player"):
    resp = await client.post("/api/auth/register", json={"username": username, "password": "pw"})
    return resp.json()["access_token"]

async def test_leaderboard_empty(client):
    resp = await client.get("/api/leaderboard")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []

async def test_leaderboard_shows_players(client):
    await _setup(client, "topplayer")
    resp = await client.get("/api/leaderboard")
    assert resp.status_code == 200
    usernames = [e["username"] for e in resp.json()["entries"]]
    assert "topplayer" in usernames

async def test_replay_not_found(client):
    resp = await client.get(f"/api/replay/{uuid.uuid4()}")
    assert resp.status_code == 404

async def test_replay_invalid_id(client):
    resp = await client.get("/api/replay/not-a-uuid")
    assert resp.status_code == 422
```

- [ ] **Step 7: 執行確認通過**

```bash
cd src/backend && pytest tests/test_api.py -v
```

Expected: 4 個 `PASSED`

- [ ] **Step 8: Commit**

```bash
git add src/backend/schemas/ src/backend/api/routes/leaderboard.py src/backend/api/routes/replay.py src/backend/main.py src/backend/tests/test_api.py
git commit -m "feat: leaderboard + replay REST APIs"
```

---

## Task 10: 前端骨架 — Vite + React + TypeScript + 共享型別 + hooks

**Files:**
- Create: `src/frontend/package.json`
- Create: `src/frontend/vite.config.ts`
- Create: `src/frontend/tsconfig.json`
- Create: `src/frontend/index.html`
- Create: `src/frontend/src/types/game.ts`
- Create: `src/frontend/src/hooks/useWebSocket.ts`
- Create: `src/frontend/src/hooks/useGameState.ts`
- Create: `src/frontend/src/App.tsx`
- Create: `src/frontend/src/main.tsx`

- [ ] **Step 1: 建立 `src/frontend/package.json`**

```json
{
  "name": "verbal-sparring-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.2",
    "jsdom": "^25.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
```

- [ ] **Step 2: 安裝依賴**

```bash
cd src/frontend && npm install
```

Expected: `node_modules/` 建立，無 error。

- [ ] **Step 3: 建立 `src/frontend/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

- [ ] **Step 4: 建立 `src/frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

- [ ] **Step 5: 建立 `src/frontend/index.html`**

```html
<!doctype html>
<html lang="zh-TW">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>唇槍舌戰</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: 建立 `src/frontend/src/types/game.ts`**

```typescript
export type HPMap = { [playerId: string]: number };

export type AttackPayload = { text: string; image?: string };

export type ServerMessage =
  | { type: "system"; message: string; hp_status: HPMap; current_turn: string }
  | {
      type: "attack";
      sender: string;
      display_text: string;
      damage: number;
      referee_comment: string;
      hp_status: HPMap;
      current_turn: string;
    }
  | {
      type: "npc_attack";
      display_text: string;
      damage: number;
      referee_comment: string;
      hp_status: HPMap;
    }
  | { type: "game_over"; message: string; winner: string }
  | { type: "turn_error"; message: string };

export type LeaderboardEntry = {
  rank: number;
  username: string;
  total_damage: number;
  wins: number;
  losses: number;
};

export type RoundSnapshot = {
  round_number: number;
  attacker: string | null;
  original_text: string | null;
  display_text: string;
  damage: number;
  referee_comment: string;
  hp_snapshot: HPMap;
};
```

- [ ] **Step 7: 建立 `src/frontend/src/hooks/useWebSocket.ts`**

```typescript
import { useRef, useEffect, useCallback } from "react";
import { ServerMessage, AttackPayload } from "../types/game";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export function useWebSocket(
  matchId: string,
  playerId: string,
  token: string,
  onMessage: (msg: ServerMessage) => void
) {
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!matchId || !token) return;
    const url = `${WS_BASE}/ws/battle/${matchId}/${playerId}?token=${token}`;
    ws.current = new WebSocket(url);

    ws.current.onmessage = (e) => {
      try {
        const msg: ServerMessage = JSON.parse(e.data);
        onMessage(msg);
      } catch {}
    };

    return () => {
      ws.current?.close();
    };
  }, [matchId, playerId, token]);

  const sendAttack = useCallback((payload: AttackPayload) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(payload));
    }
  }, []);

  return { sendAttack };
}
```

- [ ] **Step 8: 建立 `src/frontend/src/hooks/useGameState.ts`**

```typescript
import { useState, useCallback } from "react";
import { ServerMessage, HPMap } from "../types/game";

export type ChatEntry = {
  id: number;
  sender: string;
  displayText: string;
  damage?: number;
  refereeComment?: string;
};

export function useGameState(myPlayerId: string) {
  const [hp, setHp] = useState<HPMap>({});
  const [currentTurn, setCurrentTurn] = useState("");
  const [chatLog, setChatLog] = useState<ChatEntry[]>([]);
  const [gameOver, setGameOver] = useState<string | null>(null);
  const nextId = useState(0);

  const handleMessage = useCallback(
    (msg: ServerMessage) => {
      if (msg.type === "system") {
        setHp(msg.hp_status);
        setCurrentTurn(msg.current_turn);
        setChatLog((prev) => [
          ...prev,
          { id: Date.now(), sender: "系統", displayText: msg.message },
        ]);
      } else if (msg.type === "attack") {
        setHp(msg.hp_status);
        setCurrentTurn(msg.current_turn);
        setChatLog((prev) => [
          ...prev,
          {
            id: Date.now(),
            sender: msg.sender,
            displayText: msg.display_text,
            damage: msg.damage,
            refereeComment: msg.referee_comment,
          },
        ]);
      } else if (msg.type === "npc_attack") {
        setHp(msg.hp_status);
        setChatLog((prev) => [
          ...prev,
          {
            id: Date.now(),
            sender: "NPC",
            displayText: msg.display_text,
            damage: msg.damage,
            refereeComment: msg.referee_comment,
          },
        ]);
      } else if (msg.type === "game_over") {
        setGameOver(msg.winner);
        setChatLog((prev) => [
          ...prev,
          { id: Date.now(), sender: "系統", displayText: msg.message },
        ]);
      }
    },
    [myPlayerId]
  );

  const isMyTurn = currentTurn === myPlayerId;

  return { hp, currentTurn, isMyTurn, chatLog, gameOver, handleMessage };
}
```

- [ ] **Step 9: 建立 `src/frontend/src/App.tsx`**

```typescript
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import BattlePage from "./pages/BattlePage";
import LeaderboardPage from "./pages/LeaderboardPage";
import ReplayPage from "./pages/ReplayPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/battle/:matchId" element={<BattlePage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/replay/:matchId" element={<ReplayPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 10: 建立 `src/frontend/src/main.tsx`**

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 11: 寫 useGameState hook 測試**

建立 `src/frontend/src/hooks/useGameState.test.ts`：

```typescript
import { renderHook, act } from "@testing-library/react";
import { useGameState } from "./useGameState";

test("handles system message and updates hp", () => {
  const { result } = renderHook(() => useGameState("alice"));
  act(() => {
    result.current.handleMessage({
      type: "system",
      message: "遊戲開始",
      hp_status: { alice: 100, bob: 100 },
      current_turn: "alice",
    });
  });
  expect(result.current.hp).toEqual({ alice: 100, bob: 100 });
  expect(result.current.isMyTurn).toBe(true);
});

test("handles attack message and updates hp", () => {
  const { result } = renderHook(() => useGameState("alice"));
  act(() => {
    result.current.handleMessage({
      type: "attack",
      sender: "bob",
      display_text: "你好遜！",
      damage: 25,
      referee_comment: "猛",
      hp_status: { alice: 75, bob: 100 },
      current_turn: "alice",
    });
  });
  expect(result.current.hp.alice).toBe(75);
  expect(result.current.chatLog[0].damage).toBe(25);
});

test("handles game_over", () => {
  const { result } = renderHook(() => useGameState("alice"));
  act(() => {
    result.current.handleMessage({ type: "game_over", message: "結束", winner: "bob" });
  });
  expect(result.current.gameOver).toBe("bob");
});
```

- [ ] **Step 12: 執行前端測試**

```bash
cd src/frontend && npm test
```

Expected: 3 個 `PASSED`

- [ ] **Step 13: Commit**

```bash
git add src/frontend/
git commit -m "feat: frontend scaffold — Vite+React+TS, shared types, useWebSocket/useGameState hooks"
```

---

## Task 11: 前端 HomePage（登入/註冊/開局）

**Files:**
- Create: `src/frontend/src/pages/HomePage.tsx`
- Create: `src/frontend/src/pages/HomePage.test.tsx`

- [ ] **Step 1: 寫失敗的 HomePage 測試**

建立 `src/frontend/src/pages/HomePage.test.tsx`：

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HomePage from "./HomePage";

global.fetch = vi.fn();

test("renders login and register tabs", () => {
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(screen.getByText("登入")).toBeInTheDocument();
  expect(screen.getByText("註冊")).toBeInTheDocument();
});

test("shows error on login failure", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Invalid credentials" }),
  });
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  fireEvent.change(screen.getByPlaceholderText("用戶名"), { target: { value: "alice" } });
  fireEvent.change(screen.getByPlaceholderText("密碼"), { target: { value: "wrong" } });
  fireEvent.click(screen.getByRole("button", { name: "登入" }));
  await waitFor(() => {
    expect(screen.getByText(/登入失敗/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 執行確認失敗**

```bash
cd src/frontend && npm test
```

Expected: HomePage.test.tsx 的 2 個測試 FAIL（檔案不存在）

- [ ] **Step 3: 建立 `src/frontend/src/pages/HomePage.tsx`**

```typescript
import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [tab, setTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token") ?? "");
  const [myUsername, setMyUsername] = useState(localStorage.getItem("username") ?? "");
  const [opponent, setOpponent] = useState("npc");
  const navigate = useNavigate();

  async function handleAuth() {
    setError("");
    const endpoint = tab === "login" ? "/api/auth/login" : "/api/auth/register";
    const resp = await fetch(`${API}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      setError(tab === "login" ? "登入失敗：" + (data.detail ?? "") : "註冊失敗：" + (data.detail ?? ""));
      return;
    }
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("username", data.username);
    setToken(data.access_token);
    setMyUsername(data.username);
  }

  async function handleStartMatch() {
    const resp = await fetch(`${API}/api/matches`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ opponent }),
    });
    const data = await resp.json();
    if (resp.ok) {
      navigate(`/battle/${data.match_id}`, { state: { token, myUsername } });
    } else {
      setError(data.detail ?? "建立對局失敗");
    }
  }

  if (!token) {
    return (
      <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "sans-serif" }}>
        <h1>唇槍舌戰</h1>
        <div>
          <button onClick={() => setTab("login")}>登入</button>
          <button onClick={() => setTab("register")}>註冊</button>
        </div>
        <input
          placeholder="用戶名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="密碼"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={handleAuth}>{tab === "login" ? "登入" : "註冊"}</button>
        {error && <p style={{ color: "red" }}>{error}</p>}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "sans-serif" }}>
      <h1>歡迎，{myUsername}！</h1>
      <div>
        <label>對手：</label>
        <select value={opponent} onChange={(e) => setOpponent(e.target.value)}>
          <option value="npc">AI NPC</option>
        </select>
        <input
          placeholder="或輸入對手用戶名"
          onChange={(e) => setOpponent(e.target.value || "npc")}
        />
      </div>
      <button onClick={handleStartMatch}>開始對戰</button>
      <br />
      <a href="/leaderboard">排行榜</a>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}
```

- [ ] **Step 4: 執行確認通過**

```bash
cd src/frontend && npm test
```

Expected: 全部 `PASSED`（包含前面 hook 測試）

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/pages/HomePage.tsx src/frontend/src/pages/HomePage.test.tsx
git commit -m "feat: HomePage — login/register/match creation"
```

---

## Task 12: 前端 BattlePage（對戰主頁）

**Files:**
- Create: `src/frontend/src/components/HPBar.tsx`
- Create: `src/frontend/src/components/ChatLog.tsx`
- Create: `src/frontend/src/components/AttackInput.tsx`
- Create: `src/frontend/src/pages/BattlePage.tsx`
- Create: `src/frontend/src/components/HPBar.test.tsx`
- Create: `src/frontend/src/components/ChatLog.test.tsx`

- [ ] **Step 1: 寫失敗的元件測試**

建立 `src/frontend/src/components/HPBar.test.tsx`：

```typescript
import { render, screen } from "@testing-library/react";
import HPBar from "./HPBar";

test("renders hp bar with correct percentage", () => {
  render(<HPBar label="Alice" hp={75} maxHp={100} />);
  expect(screen.getByText("Alice")).toBeInTheDocument();
  expect(screen.getByText("75")).toBeInTheDocument();
  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveStyle("width: 75%");
});

test("renders red when hp is low", () => {
  render(<HPBar label="Bob" hp={15} maxHp={100} />);
  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveStyle("background-color: #e53e3e");
});
```

建立 `src/frontend/src/components/ChatLog.test.tsx`：

```typescript
import { render, screen } from "@testing-library/react";
import ChatLog from "./ChatLog";
import type { ChatEntry } from "../hooks/useGameState";

const entries: ChatEntry[] = [
  { id: 1, sender: "alice", displayText: "你好遜！", damage: 20, refereeComment: "猛" },
  { id: 2, sender: "系統", displayText: "遊戲開始" },
];

test("renders all chat entries", () => {
  render(<ChatLog entries={entries} />);
  expect(screen.getByText("你好遜！")).toBeInTheDocument();
  expect(screen.getByText("遊戲開始")).toBeInTheDocument();
});

test("shows damage amount", () => {
  render(<ChatLog entries={entries} />);
  expect(screen.getByText("-20")).toBeInTheDocument();
});
```

- [ ] **Step 2: 執行確認失敗**

```bash
cd src/frontend && npm test
```

Expected: HPBar 和 ChatLog 的測試 FAIL

- [ ] **Step 3: 建立 `src/frontend/src/components/HPBar.tsx`**

```typescript
type Props = { label: string; hp: number; maxHp?: number };

export default function HPBar({ label, hp, maxHp = 100 }: Props) {
  const pct = Math.max(0, Math.min(100, (hp / maxHp) * 100));
  const color = pct > 50 ? "#48bb78" : pct > 20 ? "#ed8936" : "#e53e3e";
  return (
    <div style={{ marginBottom: 8 }}>
      <span>{label}</span>
      <span style={{ float: "right" }}>{hp}</span>
      <div style={{ background: "#e2e8f0", borderRadius: 4, height: 12, marginTop: 4 }}>
        <div
          role="progressbar"
          aria-valuenow={hp}
          style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.3s" }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 建立 `src/frontend/src/components/ChatLog.tsx`**

```typescript
import { useEffect, useRef } from "react";
import type { ChatEntry } from "../hooks/useGameState";

type Props = { entries: ChatEntry[] };

export default function ChatLog({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "8px", background: "#1a202c", color: "#e2e8f0" }}>
      {entries.map((e) => (
        <div key={e.id} style={{ marginBottom: 6 }}>
          <strong>{e.sender}：</strong>
          {e.displayText}
          {e.damage != null && (
            <span style={{ color: "#fc8181", marginLeft: 8 }}>
              -{e.damage} 💥 {e.refereeComment}
            </span>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 5: 建立 `src/frontend/src/components/AttackInput.tsx`**

```typescript
import { useState, useRef } from "react";
import type { AttackPayload } from "../types/game";

type Props = { onSend: (p: AttackPayload) => void; disabled: boolean };

export default function AttackInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  function handleSend() {
    if (!text.trim()) return;
    onSend({ text });
    setText("");
  }

  function handleImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onSend({ text, image: reader.result as string });
    reader.readAsDataURL(file);
  }

  return (
    <div style={{ display: "flex", gap: 8, padding: 8, background: "#2d3748" }}>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && !disabled && handleSend()}
        placeholder="輸入你的攻擊..."
        disabled={disabled}
        style={{ flex: 1, padding: "6px 10px", borderRadius: 4 }}
      />
      <button onClick={() => fileRef.current?.click()} disabled={disabled}>📷</button>
      <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleImage} />
      <button onClick={handleSend} disabled={disabled || !text.trim()}>出招！</button>
    </div>
  );
}
```

- [ ] **Step 6: 建立 `src/frontend/src/pages/BattlePage.tsx`**

```typescript
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { useGameState } from "../hooks/useGameState";
import { useWebSocket } from "../hooks/useWebSocket";
import HPBar from "../components/HPBar";
import ChatLog from "../components/ChatLog";
import AttackInput from "../components/AttackInput";

export default function BattlePage() {
  const { matchId } = useParams<{ matchId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const token: string = location.state?.token ?? localStorage.getItem("token") ?? "";
  const myUsername: string = location.state?.myUsername ?? localStorage.getItem("username") ?? "Player";

  const { hp, isMyTurn, chatLog, gameOver, handleMessage } = useGameState(myUsername);
  const { sendAttack } = useWebSocket(matchId!, myUsername, token, handleMessage);

  const myHp = hp[myUsername] ?? 100;
  const opponentEntries = Object.entries(hp).filter(([k]) => k !== myUsername);
  const [opponentName, opponentHp] = opponentEntries[0] ?? ["對手", 100];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#171923", color: "#e2e8f0", fontFamily: "sans-serif" }}>
      <div style={{ padding: "12px 16px", background: "#2d3748" }}>
        <HPBar label={opponentName} hp={opponentHp as number} />
      </div>

      <ChatLog entries={chatLog} />

      <div style={{ padding: "12px 16px", background: "#2d3748" }}>
        <HPBar label={myUsername} hp={myHp} />
        <div style={{ fontSize: 12, color: isMyTurn ? "#68d391" : "#fc8181", marginTop: 4 }}>
          {isMyTurn ? "輪到你出招！" : "等待對手..."}
        </div>
      </div>

      {gameOver ? (
        <div style={{ padding: 16, textAlign: "center" }}>
          <p>{gameOver === myUsername ? "你贏了！" : "你輸了..."}</p>
          <button onClick={() => navigate("/")}>回首頁</button>
        </div>
      ) : (
        <AttackInput onSend={sendAttack} disabled={!isMyTurn} />
      )}
    </div>
  );
}
```

- [ ] **Step 7: 執行確認通過**

```bash
cd src/frontend && npm test
```

Expected: 全部 `PASSED`

- [ ] **Step 8: Commit**

```bash
git add src/frontend/src/components/ src/frontend/src/pages/BattlePage.tsx
git commit -m "feat: BattlePage with HPBar, ChatLog, AttackInput components"
```

---

## Task 13: 前端 LeaderboardPage + ReplayPage

**Files:**
- Create: `src/frontend/src/pages/LeaderboardPage.tsx`
- Create: `src/frontend/src/pages/ReplayPage.tsx`
- Create: `src/frontend/src/pages/LeaderboardPage.test.tsx`

- [ ] **Step 1: 寫失敗的 LeaderboardPage 測試**

建立 `src/frontend/src/pages/LeaderboardPage.test.tsx`：

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LeaderboardPage from "./LeaderboardPage";

global.fetch = vi.fn();

test("renders leaderboard entries", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      entries: [
        { rank: 1, username: "topgun", total_damage: 500, wins: 10, losses: 2 },
        { rank: 2, username: "player2", total_damage: 300, wins: 6, losses: 4 },
      ],
    }),
  });
  render(<MemoryRouter><LeaderboardPage /></MemoryRouter>);
  await waitFor(() => {
    expect(screen.getByText("topgun")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 執行確認失敗**

```bash
cd src/frontend && npm test
```

Expected: LeaderboardPage.test.tsx FAIL

- [ ] **Step 3: 建立 `src/frontend/src/pages/LeaderboardPage.tsx`**

```typescript
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { LeaderboardEntry } from "../types/game";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);

  useEffect(() => {
    fetch(`${API}/api/leaderboard`)
      .then((r) => r.json())
      .then((d) => setEntries(d.entries ?? []));
  }, []);

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>排行榜</h1>
      <Link to="/">← 回首頁</Link>
      <table style={{ width: "100%", marginTop: 16, borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>#</th><th>用戶名</th><th>累計傷害</th><th>勝</th><th>敗</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.rank}>
              <td>{e.rank}</td>
              <td>{e.username}</td>
              <td>{e.total_damage}</td>
              <td>{e.wins}</td>
              <td>{e.losses}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: 建立 `src/frontend/src/pages/ReplayPage.tsx`**

```typescript
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { RoundSnapshot } from "../types/game";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function ReplayPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const [rounds, setRounds] = useState<RoundSnapshot[]>([]);
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    if (!matchId) return;
    fetch(`${API}/api/replay/${matchId}`)
      .then((r) => r.json())
      .then((d) => setRounds(d.rounds ?? []));
  }, [matchId]);

  const current = rounds[frame];

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>對戰回放</h1>
      <Link to="/">← 回首頁</Link>
      {rounds.length === 0 ? (
        <p>載入中...</p>
      ) : (
        <>
          <div style={{ margin: "16px 0" }}>
            <input
              type="range"
              min={0}
              max={rounds.length - 1}
              value={frame}
              onChange={(e) => setFrame(Number(e.target.value))}
              style={{ width: "100%" }}
            />
            <p>回合 {current.round_number} / {rounds.length}</p>
          </div>
          {current && (
            <div style={{ background: "#1a202c", color: "#e2e8f0", padding: 16, borderRadius: 8 }}>
              <p><strong>攻擊者：</strong>{current.attacker ?? "NPC"}</p>
              <p><strong>攻擊內容：</strong>{current.display_text}</p>
              <p><strong>傷害：</strong>{current.damage}</p>
              <p><strong>裁判短評：</strong>{current.referee_comment}</p>
              <p><strong>HP 快照：</strong>{JSON.stringify(current.hp_snapshot)}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 5: 執行確認通過**

```bash
cd src/frontend && npm test
```

Expected: 全部 `PASSED`

- [ ] **Step 6: 確認 build 可通過**

```bash
cd src/frontend && npm run build
```

Expected: `dist/` 目錄建立，無 TypeScript error。

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/pages/
git commit -m "feat: LeaderboardPage + ReplayPage with frame slider"
```

---

## Task 14: 部署設定 — Cloudflare Pages + DNS 指南

**Files:**
- Create: `src/frontend/.env.development`
- Create: `src/frontend/.env.production`
- Create: `docs/architecture/cloudflare-deployment.md`

- [ ] **Step 1: 建立 `src/frontend/.env.development`**

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

- [ ] **Step 2: 建立 `src/frontend/.env.production`（填入真實網域）**

```
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

- [ ] **Step 3: 確認 `.gitignore` 不忽略 `.env.production`**

在 repo 根目錄的 `.gitignore` 確認有以下規則（只忽略含 secret 的 backend .env，不忽略前端 .env.production）：

```
src/backend/.env
!src/frontend/.env.production
!src/frontend/.env.development
```

- [ ] **Step 4: 建立 `docs/architecture/cloudflare-deployment.md`**

```markdown
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
```

- [ ] **Step 5: 執行完整後端測試確認全部通過**

```bash
cd src/backend && pytest -v
```

Expected: 全部 `PASSED`，無 FAIL。

- [ ] **Step 6: 執行完整前端測試確認全部通過**

```bash
cd src/frontend && npm test && npm run build
```

Expected: 全部測試 PASSED，build 成功。

- [ ] **Step 7: 最終 Commit**

```bash
git add src/frontend/.env.development src/frontend/.env.production docs/architecture/
git commit -m "feat: Cloudflare Pages + DNS deployment guide, frontend env configs"
```

---

## 實作完成後的驗收清單

- [ ] `docker compose up` 後後端可正常啟動連線 PostgreSQL
- [ ] `POST /api/auth/register` 可建立帳號
- [ ] `POST /api/matches` 可建立人機對局，取得 `match_id`
- [ ] WebSocket 連線 `/ws/battle/{match_id}/{username}?token=...` 可進入房間
- [ ] 送出攻擊後 NPC 自動回應，HP 正確扣減
- [ ] 對局結束後 `GET /api/replay/{match_id}` 可取得完整回合紀錄
- [ ] `GET /api/leaderboard` 回傳玩家排行
- [ ] 前端 `npm run build` 無 TypeScript error
- [ ] Cloudflare Pages build 設定指向 `src/frontend`
