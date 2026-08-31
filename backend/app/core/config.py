"""Application configuration.

All settings come from environment variables. See `.env.example` in the repository root for the
full list and `AI_BUILD_SPEC.md` section 29 for the specification.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """Runtime configuration read from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    redis_url: str

    secret_key: str = Field(min_length=MIN_SECRET_KEY_LENGTH)
    access_token_expire_minutes: int = 60

    # Comma-separated in the environment because env vars carry no list type.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read from the environment once."""
    return Settings()
