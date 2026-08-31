"""Tests for SQLAlchemy engine, session and Alembic infrastructure."""

from pathlib import Path
from subprocess import run
from sys import executable
from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.config import Settings
from app.core.database import (
    Base,
    create_engine_from_settings,
    create_session_factory,
    get_db_session,
    normalize_database_url,
)
from app.main import create_app

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _sqlite_settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"database_url": "sqlite:///:memory:"})


def test_base_is_sqlalchemy_declarative_base() -> None:
    assert issubclass(Base, DeclarativeBase)


def test_postgresql_urls_are_rewritten_to_psycopg() -> None:
    assert (
        normalize_database_url("postgresql://teamos:change-me@postgres:5432/teamos")
        == "postgresql+psycopg://teamos:change-me@postgres:5432/teamos"
    )
    assert (
        normalize_database_url("postgres://teamos:change-me@postgres:5432/teamos")
        == "postgresql+psycopg://teamos:change-me@postgres:5432/teamos"
    )


def test_explicit_driver_urls_are_left_unchanged() -> None:
    url = "postgresql+psycopg://teamos:change-me@postgres:5432/teamos"
    assert normalize_database_url(url) == url
    assert normalize_database_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_session_executes_sql_and_closes(settings: Settings) -> None:
    engine = create_engine_from_settings(_sqlite_settings(settings))
    factory = create_session_factory(engine)
    session = factory()
    try:
        assert session.execute(text("SELECT 1")).scalar() == 1
    finally:
        session.close()
    assert not session.in_transaction()
    engine.dispose()


def test_get_db_session_dependency_yields_a_working_session(settings: Settings) -> None:
    app = create_app(_sqlite_settings(settings))

    @app.get("/_db")
    def ping_db(session: Annotated[Session, Depends(get_db_session)]) -> dict[str, int]:
        value = session.execute(text("SELECT 1")).scalar_one()
        return {"value": int(value)}

    with TestClient(app) as client:
        response = client.get("/_db")

    assert response.status_code == 200
    assert response.json() == {"value": 1}


def test_alembic_head_is_organizations_revision() -> None:
    assert (_BACKEND_ROOT / "alembic.ini").is_file()
    assert (_BACKEND_ROOT / "alembic" / "env.py").is_file()
    assert (_BACKEND_ROOT / "alembic" / "script.py.mako").is_file()
    revision_files = list((_BACKEND_ROOT / "alembic" / "versions").glob("*.py"))
    assert sorted(path.name for path in revision_files) == [
        "0001_create_users.py",
        "0002_create_organizations.py",
    ]

    result = run(
        [executable, "-m", "alembic", "heads"],
        cwd=_BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "0002_create_organizations" in result.stdout
