from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    """Create an async SQLAlchemy engine for the given URL.

    Args:
        url: SQLAlchemy-compatible async database URL.

    Returns:
        An AsyncEngine instance.
    """
    return create_async_engine(url, echo=False)


def make_session_factory(engine):
    """Create an async session factory bound to the given engine.

    Args:
        engine: An AsyncEngine instance.

    Returns:
        An async_sessionmaker that produces AsyncSession instances.
    """
    return async_sessionmaker(engine, expire_on_commit=False)


from src.backend.core.config import settings  # noqa: E402

engine = make_engine(settings.database_url)
SessionFactory = make_session_factory(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session.

    Yields:
        An AsyncSession for the current request.
    """
    async with SessionFactory() as session:
        yield session


def _import_models() -> None:
    """Import all ORM models so that Base.metadata is fully populated.

    This must be called before ``Base.metadata.create_all`` during test
    setup or Alembic migrations.

    Silently skips models that have not been implemented yet so that tests
    which do not require database tables (e.g. ``/health``) can run before
    all model modules are written.
    """
    try:
        from src.backend.models import GameRound, Match, NpcMemory, Player  # noqa: F401
    except ImportError:
        pass
