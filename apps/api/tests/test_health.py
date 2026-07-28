import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend() -> str:
    """Run asynchronous API tests on the asyncio backend."""

    return "asyncio"


@pytest.mark.anyio
async def test_health() -> None:
    """Return engine metadata from the liveness endpoint."""

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "engine": "available",
        "rulesVersion": "chinese-durak/0.2.0-draft",
    }
