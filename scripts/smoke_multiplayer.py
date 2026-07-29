"""Run a real two-client HTTP and WebSocket multiplayer smoke test."""

import argparse
import asyncio
import json
from typing import Any
from urllib.parse import urlparse

import httpx
from websockets.asyncio.client import ClientConnection, connect


def websocket_url(api_url: str, room_id: str, token: str) -> str:
    """Build a WebSocket endpoint from an HTTP API address."""

    parsed = urlparse(api_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return (
        f"{scheme}://{parsed.netloc}/api/rooms/{room_id}/ws"
        f"?token={token}"
    )


async def receive_snapshot(
    socket: ClientConnection,
    *,
    status: str | None = None,
    minimum_version: int | None = None,
) -> dict[str, Any]:
    """Receive messages until the requested private snapshot arrives."""

    async with asyncio.timeout(8):
        while True:
            payload = json.loads(await socket.recv())

            if payload.get("type") != "snapshot":
                continue

            if status is not None and payload["room"]["status"] != status:
                continue

            game = payload.get("game")

            if (
                minimum_version is not None
                and (game is None or game["version"] < minimum_version)
            ):
                continue

            return payload


async def expect_pong(socket: ClientConnection) -> None:
    """Verify the heartbeat message used by the browser."""

    await socket.send(json.dumps({"type": "ping"}))

    async with asyncio.timeout(8):
        while True:
            payload = json.loads(await socket.recv())

            if payload.get("type") == "pong":
                return


async def run(api_url: str) -> None:
    """Create a room, connect two sockets, and apply one legal move."""

    async with httpx.AsyncClient(
        base_url=api_url,
        timeout=8,
        trust_env=False,
    ) as client:
        for attempt in range(40):
            try:
                response = await client.get("/health")

                if response.is_success:
                    break
            except httpx.HTTPError:
                pass

            if attempt == 39:
                raise RuntimeError("API did not become healthy")

            await asyncio.sleep(0.1)

        created = await client.post(
            "/api/rooms",
            json={"nickname": "Smoke Host", "playerCount": 2},
        )
        created.raise_for_status()
        host = created.json()

        async with connect(
            websocket_url(
                api_url,
                host["roomId"],
                host["seatToken"],
            ),
            proxy=None,
        ) as host_socket:
            await receive_snapshot(host_socket, status="waiting")
            await expect_pong(host_socket)

            joined = await client.post(
                f"/api/rooms/{host['roomId']}/join",
                json={"nickname": "Smoke Guest"},
            )
            joined.raise_for_status()
            guest = joined.json()

            async with connect(
                websocket_url(
                    api_url,
                    guest["roomId"],
                    guest["seatToken"],
                ),
                proxy=None,
            ) as guest_socket:
                host_view = await receive_snapshot(
                    host_socket,
                    status="playing",
                )
                guest_view = await receive_snapshot(
                    guest_socket,
                    status="playing",
                )
                attacker = host_view["game"]["mainAttacker"]
                actor_view = host_view if attacker == 0 else guest_view
                actor_socket = host_socket if attacker == 0 else guest_socket
                action = actor_view["game"]["legalActions"][0]

                await actor_socket.send(
                    json.dumps(
                        {
                            "type": "action",
                            "requestId": "smoke-action-1",
                            "expectedVersion": actor_view["game"]["version"],
                            "action": action,
                        }
                    )
                )

                await receive_snapshot(
                    host_socket,
                    minimum_version=2,
                )
                await receive_snapshot(
                    guest_socket,
                    minimum_version=2,
                )

    print("Multiplayer smoke test passed")


def main() -> None:
    """Parse arguments and execute the asynchronous smoke test."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
    )
    arguments = parser.parse_args()
    asyncio.run(run(arguments.api_url.rstrip("/")))


if __name__ == "__main__":
    main()
