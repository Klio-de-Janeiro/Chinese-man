from dataclasses import dataclass
from functools import lru_cache
from os import getenv


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    database_url: str
    rules_version: str
    bot_model_path: str
    bot_metadata_path: str
    bot_move_delay_seconds: float


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
        bot_model_path=getenv(
            "BOT_MODEL_PATH",
            "models/bot_v1.onnx",
        ),
        bot_metadata_path=getenv(
            "BOT_METADATA_PATH",
            "models/bot_v1_metadata.json",
        ),
        bot_move_delay_seconds=float(
            getenv("BOT_MOVE_DELAY_MS", "450")
        )
        / 1000.0,
    )
