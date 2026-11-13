# Portfolio backend

FastAPI + PostgreSQL (SQLAlchemy 2.0 async, asyncpg) with Alembic migrations.

## Configuration

Copy `.env.example` to `.env`. Main variables: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`.

## Settings worth knowing

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key (long random string) |
| `CORS_ORIGINS` | JSON list of allowed frontend origins |
| `FRONTEND_URL` | Public URL of the frontend, e.g. `https://portfoliohub.thikana.cc`. Used for share links and link previews. |

## Public profile links, link previews and live previews

- A profile can have a short link name: `PUT /portfolio/` with `slug` -> `/u/<slug>` in the frontend; `GET /user/slug/<slug>` resolves it.
- `GET /og/<slug-or-id>` returns the Open Graph / Twitter tags for a profile and `/og/<ref>/image.png` a generated 1200x630 preview image.
  The frontend's nginx sends link-preview crawlers (LinkedIn, Slack, WhatsApp, ...) here instead of the single-page app.
- `GET /preview/embeddable/<project_id>` tells the frontend whether a project's `live_url` may be shown in an iframe
  (checks X-Frame-Options / CSP `frame-ancestors`; private and internal addresses are refused, results cached 10 minutes).

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
