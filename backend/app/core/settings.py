"""Application settings, read from environment variables and the repository's .env file.

Real environment variables win over the .env file. The database password is held as a
secret value, so it is never printed or logged by accident.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is backend/app/core/settings.py, so the repository root is three folders above it.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5433
    postgres_db: str = "verifigst"
    postgres_user: str = "verifigst"
    postgres_password: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    return Settings()
