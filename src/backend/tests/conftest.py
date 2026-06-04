import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config import settings
from src.backend.core.database import Base, get_session, make_engine, make_session_factory

# Prefer the configured test URL; fall back to in-memory SQLite when postgres
# is not available in the current environment (e.g. CI without a pg container).
_CONFIGURED_URL = (
    settings.test_database_url
    or "postgresql+asyncpg://vsuser:vspass@localhost:5433/verbal_sparring_test"
)
_SQLITE_FALLBACK = "sqlite+aiosqlite:///:memory:"


async def _postgres_reachable(url: str) -> bool:
    """Return True if a quick async connection to the postgres URL succeeds."""
    from sqlalchemy.ext.asyncio import create_async_engine

    eng = create_async_engine(url, echo=False, pool_pre_ping=True)
    try:
        async with eng.connect():
            return True
    except Exception:
        return False
    finally:
        await eng.dispose()


def _resolve_test_url(configured: str) -> str:
    """Synchronously probe the configured URL; fall back to SQLite if unavailable."""
    if not configured.startswith("postgresql"):
        return configured

    import asyncio
    import socket

    # Quick TCP check first — cheaper than a full asyncpg handshake.
    try:
        netloc = configured.split("@")[1].split("/")[0]
        host, _, port_str = netloc.partition(":")
        port = int(port_str) if port_str else 5432
        socket.create_connection((host, port), timeout=1).close()
    except Exception:
        return _SQLITE_FALLBACK

    # TCP open — verify credentials with a real async connection.
    try:
        loop = asyncio.new_event_loop()
        reachable = loop.run_until_complete(_postgres_reachable(configured))
        loop.close()
        return configured if reachable else _SQLITE_FALLBACK
    except Exception:
        return _SQLITE_FALLBACK


RESOLVED_URL = _resolve_test_url(_CONFIGURED_URL)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Session-scoped engine that creates and tears down the test schema."""
    from src.backend.core.database import _import_models

    _import_models()
    eng = make_engine(RESOLVED_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(test_engine):
    """Function-scoped session with SAVEPOINT isolation that rolls back after each test."""
    async with test_engine.connect() as conn:
        await conn.begin()
        nested = await conn.begin_nested()  # SAVEPOINT
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()  # rolls back even committed work within savepoint


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """AsyncClient wired to the FastAPI app with the test DB injected."""
    from src.backend.main import app

    app.dependency_overrides[get_session] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
