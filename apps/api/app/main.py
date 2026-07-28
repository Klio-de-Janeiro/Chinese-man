from chinese_durak import RULES_VERSION
from fastapi import FastAPI, HTTPException

from .database import database_is_ready
from .settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Chinese Durak API",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return process and native-engine health."""

    return {
        "status": "ok",
        "engine": "available",
        "rulesVersion": str(RULES_VERSION),
    }


@app.get("/ready")
async def readiness() -> dict[str, str]:
    """Return readiness after checking PostgreSQL."""

    try:
        await database_is_ready()
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from error

    return {
        "status": "ready",
        "database": "available",
        "rulesVersion": settings.rules_version,
    }
