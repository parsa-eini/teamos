"""SQLAlchemy engine, session factory and declarative base.

Services own transaction boundaries (`AI_BUILD_SPEC.md` section 40). The session dependency
yields an open session and closes it afterwards; it does not commit.
"""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def normalize_database_url(url: str) -> str:
    """Use the psycopg (v3) driver for unadorned PostgreSQL URLs.

    `.env.example` and Compose historically used `postgresql://`. SQLAlchemy treats that scheme as
    psycopg2, which is not a project dependency.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


def create_engine_from_settings(settings: Settings) -> Engine:
    return create_engine(
        normalize_database_url(settings.database_url),
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


def get_db_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped SQLAlchemy session."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()
