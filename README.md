# Team Management Product

A lightweight team-management platform for engineering managers and team leads. It covers
organizations, teams, members, projects, tasks, goals, check-ins, a manager dashboard, and
in-app notifications.

`AI_BUILD_SPEC.md` is the source of truth for scope and architecture. `IMPLEMENTATION_PLAN.md`
describes the staged build order, and `DEFINITION_OF_DONE.md` defines when work is complete.

## Architecture

Modular monolith:

- **backend** — Python 3.12+, FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic
- **website** — public marketing and sign-up application (React + TypeScript + Vite)
- **panel** — authenticated management application (React + TypeScript + Vite)
- **PostgreSQL** — primary datastore
- **Redis** — caching and future background processing
- **Docker Compose** — local development environment

## Repository structure

```text
backend/    FastAPI application
website/    Public-facing React application
panel/      Authenticated React application
docs/       Architecture, database, API documentation and decision records
.cursor/    Repository rules for AI coding agents
```

## Local development

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (only needed to run backend tooling outside Docker)
- Node.js 20+ (only needed to run frontend tooling outside Docker)

### Setup

1. Clone the repository.
2. Create your local environment file:

```bash
cp .env.example .env
```

3. Set your own values in `.env`. At minimum replace `SECRET_KEY` and `POSTGRES_PASSWORD`.
   `.env` is git-ignored and must never be committed.

### Running the stack

`.env` must exist before starting the stack, because Compose reads the database, cache and
authentication settings from it.

```bash
docker compose up --build
```

Services and the ports they are published on:

| Service    | URL / address            |
| ---------- | ------------------------ |
| backend    | <http://localhost:8000>  |
| website    | <http://localhost:5173>  |
| panel      | <http://localhost:5174>  |
| postgres   | `localhost:5432`         |
| redis      | `localhost:6379`         |

The backend waits for PostgreSQL and Redis to report healthy before it starts. PostgreSQL data
survives restarts in the `postgres-data` volume; use `docker compose down -v` to discard it.

The `backend`, `website` and `panel` images build from their own source directories, so they only
build once the corresponding application code exists (Stage 2 for the backend, Stage 12 for the
panel, Stage 13 for the website). Until then, start only the datastores:

```bash
docker compose up postgres redis
```

Useful commands:

```bash
docker compose ps                 # service status
docker compose logs -f backend    # follow one service
docker compose down               # stop, keeping data
docker compose down -v            # stop and delete volumes
```

## Configuration

All configuration comes from environment variables. `.env.example` lists every variable the
project expects and is the reference for local and deployed environments.

## Security

- Never commit `.env` or any other secret material.
- Never log passwords, password hashes, tokens or authorization headers.
- Authorization and organization isolation are enforced by the backend, never by the frontend.

## Current status

Phase 1 / MVP, Stage 11 (notifications). See `IMPLEMENTATION_PLAN.md` for the remaining stages.
