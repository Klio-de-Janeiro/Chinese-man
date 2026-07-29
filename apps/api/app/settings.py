from dataclasses import dataclass
from functools import lru_cache
from os import getenv


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    database_url: str
    rules_version: str


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings(
        database_url=getenv(
            "DATABASE_URL",
            (
                "postgresql+asyncpg://chinese_durak:change_me"
                "@localhost:5432/chinese_durak"
            ),
        ),
        rules_version=getenv(
            "RULES_VERSION",
            "chinese-durak/0.2.1-draft",
        ),
    )
