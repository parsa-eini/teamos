# Backend

FastAPI application for the team management product.

Stack: Python 3.12+, FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic, PostgreSQL, Redis, pytest,
Ruff.

Architecture: `router → service → repository → database`. See `AI_BUILD_SPEC.md` sections 6, 22 and
38 for the module layout and layering rules.

## Layout

```text
app/
├── main.py          Application factory and the /health endpoint
├── core/            Configuration, logging, database, Redis and security
├── common/          Exceptions, error handlers, pagination, dependencies and response envelopes
├── modules/         Business modules (auth, users, organizations, teams, projects, tasks, goals, ...)
└── tests/           Test suite
alembic/             Migration environment
alembic.ini
```

## Running

The backend normally runs through Docker Compose from the repository root:

```bash
docker compose up backend
```

The API is then served on <http://localhost:8000>, with OpenAPI documentation at
<http://localhost:8000/docs> and a liveness check at <http://localhost:8000/health>.

To run it directly instead, from this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --editable ".[dev]"
uvicorn app.main:create_app --factory --reload
```

`DATABASE_URL`, `REDIS_URL` and `SECRET_KEY` have no defaults and must be present in the
environment, otherwise startup fails with a validation error.

Database migrations use Alembic from this directory:

```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
```

Revisions create the `users`, `organizations`, `organization_memberships`, `teams`,
`team_memberships`, `projects`, `tasks`, and `goals` tables. After changing models, generate a
revision and apply it with `alembic upgrade head`.

## Configuration

Configuration is read from environment variables by `app/core/config.py`. The authoritative list of
variables is `.env.example` in the repository root.

`DATABASE_URL` should use the `postgresql+psycopg://` scheme. Unadorned `postgresql://` URLs are
rewritten to that driver at runtime.

## Quality checks

```bash
pytest          # tests
ruff check .    # linting
ruff format .   # formatting
mypy app        # type checking
```
