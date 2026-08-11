# Team Management Product

A lightweight team-management platform for engineering managers and team leads. It covers
organizations, teams, members, projects, tasks, goals, check-ins and a manager dashboard.

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

Docker Compose is introduced in Stage 1 of `IMPLEMENTATION_PLAN.md`. Once it exists, the whole
development environment starts with:

```bash
docker compose up --build
```

Until then only the repository foundation is in place; the backend and frontend applications are
added in later stages.

## Configuration

All configuration comes from environment variables. `.env.example` lists every variable the
project expects and is the reference for local and deployed environments.

## Security

- Never commit `.env` or any other secret material.
- Never log passwords, password hashes, tokens or authorization headers.
- Authorization and organization isolation are enforced by the backend, never by the frontend.

## Current status

Phase 1 / MVP, Stage 0 (repository foundation). See `IMPLEMENTATION_PLAN.md` for the remaining
stages.
