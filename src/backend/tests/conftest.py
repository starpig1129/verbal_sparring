import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.backend.core.config import settings
from src.backend.core.database import Base, get_session, make_session_factory

# Prefer the configured test URL; fall back to in-memory SQLite when postgres
# is not available in the current environment (e.g. CI without a pg container).
_CONFIGURED_URL = (
    settings.test_database_url
    or "postgresql+asyncpg://vsuser:vspass@localhost:5433/verbal_sparring_test"
)
_SQLITE_FALLBACK = "sqlite+aiosqlite:///:memory:"


async def _postgres_reachable(url: str) -> bool:
    """Return True if a quick async connection to the postgres URL succeeds."""
    eng = create_async_engine(url, echo=False, pool_pre_ping=True, poolclass=NullPool)
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
        import warnings
        warnings.warn(
            "PostgreSQL unavailable — falling back to SQLite. "
            "Tests involving JSONB (GameRound, NpcMemory) may fail. "
            "Run: docker compose up -d postgres_test",
            UserWarning,
            stacklevel=2,
        )
        return _SQLITE_FALLBACK

    # TCP open — verify credentials with a real async connection.
    try:
        loop = asyncio.new_event_loop()
        reachable = loop.run_until_complete(_postgres_reachable(configured))
        loop.close()
        if reachable:
            return configured
        import warnings
        warnings.warn(
            "PostgreSQL unavailable — falling back to SQLite. "
            "Tests involving JSONB (GameRound, NpcMemory) may fail. "
            "Run: docker compose up -d postgres_test",
            UserWarning,
            stacklevel=2,
        )
        return _SQLITE_FALLBACK
    except Exception:
        import warnings
        warnings.warn(
            "PostgreSQL unavailable — falling back to SQLite. "
            "Tests involving JSONB (GameRound, NpcMemory) may fail. "
            "Run: docker compose up -d postgres_test",
            UserWarning,
            stacklevel=2,
        )
        return _SQLITE_FALLBACK


RESOLVED_URL = _resolve_test_url(_CONFIGURED_URL)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Session-scoped engine used ONLY for schema setup and teardown.

    NullPool is used so that no asyncpg connections are held open between
    operations, which prevents "Future attached to a different loop" errors
    that occur when pooled connections created in one event loop are reused
    from another.
    """
    from src.backend.core.database import _import_models

    _import_models()
    eng = create_async_engine(RESOLVED_URL, echo=False, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(test_engine):
    """Function-scoped session backed by a fresh NullPool engine.

    A new engine (NullPool) is created per test so that asyncpg connections
    are always bound to the current event loop.  Tables are truncated after
    each test to keep tests isolated.

    Note: the ``test_engine`` argument is kept as a dependency to guarantee
    that ``Base.metadata.create_all`` has run before this fixture is used.
    """
    # Create a per-test engine so connections are bound to the current loop.
    eng = create_async_engine(RESOLVED_URL, echo=False, poolclass=NullPool)
    session_factory = make_session_factory(eng)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        # Truncate all tables to isolate the next test.
        async with eng.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
        await eng.dispose()


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """AsyncClient wired to the FastAPI app with the test DB injected."""
    from src.backend.main import app

    async def _override():
        yield db
    app.dependency_overrides[get_session] = _override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
