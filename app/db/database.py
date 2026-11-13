from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)

# expire_on_commit=False so objects stay readable after commit (responses are built after commit)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request (shared by all dependencies of that request)."""
    async with SessionLocal() as session:
        yield session
