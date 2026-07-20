from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Neon (and most managed Postgres) connection strings come with
# ?sslmode=require appended — that parameter name is the psycopg2/libpq
# convention. asyncpg doesn't recognize "sslmode" at all and crashes on
# it directly, so we strip that from the URL (see .env.example / README)
# and pass SSL the way asyncpg actually expects it instead.
connect_args = {"ssl": "require"} if settings.database_url.startswith("postgresql") else {}

engine = create_async_engine(settings.database_url, connect_args=connect_args)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields one database session per use, committing on success and
    rolling back on any exception — usage:

        async with get_session() as session:
            ...

    `expire_on_commit=False` matters here: by default, SQLAlchemy clears
    an object's loaded attributes after commit, forcing a fresh query the
    next time you touch them. We turn that off because we often want to
    read back data (e.g. a transcript's final_answer) immediately after
    saving it, without an unnecessary extra round trip to the database.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
