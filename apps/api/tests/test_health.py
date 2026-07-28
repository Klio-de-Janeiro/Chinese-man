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


@pytest.mark.anyio
async def test_room_http_flow_preserves_private_hands() -> None:
    """Create and join a room through the public HTTP contract."""

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        created = await client.post(
            "/api/rooms",
            json={
                "nickname": "Klio",
                "playerCount": 2,
            },
        )
        assert created.status_code == 201
        host = created.json()

        joined = await client.post(
            f"/api/rooms/{host['roomId']}/join",
            json={"nickname": "Михаил"},
        )
        assert joined.status_code == 200

        state_response = await client.get(
            f"/api/rooms/{host['roomId']}",
            params={"token": host["seatToken"]},
        )
        assert state_response.status_code == 200

    state = state_response.json()
    assert state["room"]["status"] == "paused"
    assert len(state["players"][0]["hand"]) == 6
    assert "hand" not in state["players"][1]
