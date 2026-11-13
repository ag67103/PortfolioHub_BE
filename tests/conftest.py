"""
API tests run against a real PostgreSQL database.

    createdb portfolio_test
    DATABASE_URL=postgresql://user@localhost/portfolio_test alembic upgrade head
    DATABASE_URL=postgresql://user@localhost/portfolio_test pytest tests

The database is WIPED at the start of the run, so its name must end in "_test".
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import settings

if not settings.database_url.rsplit("/", 1)[-1].split("?")[0].endswith("_test"):
    raise RuntimeError("Refusing to run tests: DATABASE_URL must point at a database whose name ends in _test")


@pytest.fixture(scope="session")
def client():
    from app.main import app

    # One TestClient for the whole session: a single event loop for the asyncpg connection pool
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def _wipe(client):
    import asyncio
    from app.db.database import engine

    async def wipe():
        async with engine.begin() as conn:
            await conn.execute(text(
                "TRUNCATE messages, access_tokens, awards, certifications, educations, experiences, projects, skills, users CASCADE"
            ))

    client.portal.call(wipe)  # run on the app's own event loop
    yield
