"""Tests for application configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_ENV_VARS = (
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "CORS_ORIGINS",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep these tests independent of whatever is set in the developer's own environment."""
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def build_settings(cors_origins: str = "") -> Settings:
    return Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        secret_key="test-secret-key",
        cors_origins=cors_origins,
    )


def test_access_token_expiry_defaults_to_sixty_minutes() -> None:
    assert build_settings().access_token_expire_minutes == 60


def test_cors_origins_are_split_on_commas() -> None:
    settings = build_settings("http://a.test,http://b.test")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_cors_origins_tolerate_surrounding_whitespace() -> None:
    settings = build_settings(" http://a.test , http://b.test ")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_empty_cors_origins_yields_no_origins() -> None:
    assert build_settings().cors_origin_list == []


def test_missing_required_settings_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings()


def test_settings_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://env:env@postgres:5432/env")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SECRET_KEY", "from-environment")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    settings = Settings()

    assert settings.secret_key == "from-environment"
    assert settings.access_token_expire_minutes == 15
    assert settings.cors_origin_list == ["http://localhost:5173"]
