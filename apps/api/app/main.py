from typing import Any

from chinese_durak import RULES_VERSION
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import database_is_ready
from .rooms import RoomError, RoomService
from .schemas import CreateRoomRequest, JoinRoomRequest
from .settings import get_settings

settings = get_settings()
room_service = RoomService()

app = FastAPI(
    title="Chinese Durak API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RoomError)
async def room_error_handler(
    _request: Request,
    error: RoomError,
) -> JSONResponse:
    """Return stable JSON for room protocol failures."""

    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
            }
        },
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


@app.post("/api/rooms", status_code=201)
async def create_room(
    request: CreateRoomRequest,
) -> dict[str, Any]:
    """Create a private room and return its host credentials."""

    room, seat = await room_service.create_room(
        request.nickname,
        request.player_count,
    )
    return room_service.credentials(room, seat)


@app.post("/api/rooms/{room_id}/join")
async def join_room(
    room_id: str,
    request: JoinRoomRequest,
) -> dict[str, Any]:
    """Join a private room using its invitation code."""

    room, seat = await room_service.join_room(
        room_id,
        request.nickname,
    )
    return room_service.credentials(room, seat)


@app.get("/api/rooms/{room_id}")
async def get_room_state(
    room_id: str,
    token: str,
) -> dict[str, Any]:
    """Return a private reconnect snapshot for one seat."""

    room = room_service.get_room(room_id)
    seat = room_service.authenticate(room, token)
    return room_service.snapshot(room, seat)


@app.websocket("/api/rooms/{room_id}/ws")
async def room_socket(
    websocket: WebSocket,
    room_id: str,
    token: str,
) -> None:
    """Stream private room snapshots and receive game commands."""

    try:
        room = room_service.get_room(room_id)
        seat = room_service.authenticate(room, token)
    except RoomError as error:
        await websocket.close(
            code=4401,
            reason=error.message,
        )
        return

    await room_service.connect(room, seat, websocket)

    try:
        while True:
            message = await websocket.receive_json()

            try:
                await room_service.handle_message(
                    room,
                    seat,
                    websocket,
                    message,
                )
            except RoomError as error:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": {
                            "code": error.code,
                            "message": error.message,
                        },
                        "requestId": message.get("requestId"),
                    }
                )
                await websocket.send_json(
                    room_service.snapshot(room, seat)
                )
    except WebSocketDisconnect:
        pass
    finally:
        await room_service.disconnect(room, seat, websocket)
