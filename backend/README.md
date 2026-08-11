# Backend

FastAPI application for the team management product.

Stack: Python 3.12+, FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic, PostgreSQL, Redis, pytest,
Ruff.

Architecture: `router → service → repository → database`. See `AI_BUILD_SPEC.md` sections 6, 22 and
38 for the module layout and layering rules.

The application itself is implemented in Stage 2 of `IMPLEMENTATION_PLAN.md`. This directory is
currently a placeholder created in Stage 0.
