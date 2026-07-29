from typing import Any

import pytest
from app.rooms import RoomError, RoomService


class FakeWebSocket:
    """Capture room messages without a network server."""

    def __init__(self) -> None:
        """Initialize an empty message buffer."""

        self.accepted = False
        self.messages: list[dict[str, Any]] = []

    async def accept(self) -> None:
        """Record a successful WebSocket handshake."""

        self.accepted = True

    async def send_json(self, payload: dict[str, Any]) -> None:
        """Store one private server message."""

        self.messages.append(payload)


@pytest.fixture
def anyio_backend() -> str:
    """Run asynchronous tests on asyncio."""

    return "asyncio"


@pytest.mark.anyio
async def test_private_room_starts_and_hides_opponent_hand() -> None:
    """Start a two-player game and verify private projections."""

    service = RoomService()
    room, host = await service.create_room("Klio", 2)
    host_socket = FakeWebSocket()
    await service.connect(room, host, host_socket)  # type: ignore[arg-type]

    room, guest = await service.join_room(room.room_id, "Михаил")
    guest_socket = FakeWebSocket()
    await service.connect(room, guest, guest_socket)  # type: ignore[arg-type]

    host_view = service.snapshot(room, host)
    guest_view = service.snapshot(room, guest)

    assert host_view["room"]["status"] == "playing"
    assert host_view["game"]["version"] == 1
    trump_card = host_view["game"]["trumpCard"]
    assert isinstance(trump_card, int)
    assert host_view["game"]["trump"] == (
        "clubs",
        "diamonds",
        "hearts",
        "spades",
    )[trump_card // 13]
    assert len(host_view["players"][0]["hand"]) == 6
    assert "hand" not in host_view["players"][1]
    assert len(guest_view["players"][1]["hand"]) == 6
    assert "hand" not in guest_view["players"][0]


@pytest.mark.anyio
async def test_action_version_rejects_stale_command() -> None:
    """Accept one engine action and reject its stale replay."""

    service = RoomService()
    room, host = await service.create_room("Klio", 2)
    room, guest = await service.join_room(room.room_id, "Михаил")
    await service.connect(
        room,
        host,
        FakeWebSocket(),  # type: ignore[arg-type]
    )
    await service.connect(
        room,
        guest,
        FakeWebSocket(),  # type: ignore[arg-type]
    )

    assert room.engine is not None
    state = room.engine.state
    actor = room.players[state["main_attacker"]]
    action = service.snapshot(room, actor)["game"]["legalActions"][0]

    await service.apply_action(
        room,
        actor,
        expected_version=state["version"],
        payload=action,
    )

    with pytest.raises(RoomError, match="Состояние изменилось"):
        await service.apply_action(
            room,
            actor,
            expected_version=state["version"],
            payload=action,
        )


@pytest.mark.anyio
async def test_ping_returns_pong() -> None:
    """Keep the heartbeat contract used by the browser reconnect loop."""

    service = RoomService()
    room, host = await service.create_room("Klio", 2)
    socket = FakeWebSocket()

    await service.handle_message(
        room,
        host,
        socket,  # type: ignore[arg-type]
        {"type": "ping"},
    )

    assert socket.messages == [{"type": "pong"}]
