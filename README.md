# Portfolio backend

FastAPI + PostgreSQL (SQLAlchemy 2.0 async, asyncpg) with Alembic migrations.

## Configuration

Copy `.env.example` to `.env`. Main variables: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`.

## Database

```bash
alembic upgrade head                                   # create / update the schema
alembic revision --autogenerate -m "describe change"   # after changing app/models
```

The container runs `alembic upgrade head` on every start. Run `alembic` from the project root, not as
`python -m alembic` (the local `alembic/` folder shadows the package there).

## Tests

Tests need a real Postgres. The database is wiped, so its name must end in `_test`.

```bash
createdb portfolio_test
export DATABASE_URL=postgresql://user@localhost/portfolio_test
alembic upgrade head && pytest tests
```

## Migrating old MongoDB data

```bash
pip install pymongo
python scripts/migrate_mongo_to_postgres.py --mongo-url mongodb://localhost:27017 --mongo-db portfolio --dry-run
python scripts/migrate_mongo_to_postgres.py --mongo-url mongodb://localhost:27017 --mongo-db portfolio
```

Safe to re-run. Sessions are not copied, so everyone signs in again.
