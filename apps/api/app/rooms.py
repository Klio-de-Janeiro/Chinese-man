"""In-memory room orchestration around the authoritative C++ engine."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from random import Random
from typing import Any

from chinese_durak import (
    RULES_VERSION,
    Action,
    ActionKind,
    GameEngine,
    GameError,
    Phase,
    Suit,
    card_name,
)
from chinese_durak.ml.agents import HeuristicAgent
from chinese_durak.ml.constants import MAX_HISTORY
from chinese_durak.ml.contracts import PublicAction
from chinese_durak.ml.native import action_from_native, phase_name
from chinese_durak.ml.observation import ObservationBuilder
from chinese_durak.ml.runtime import FallbackBotRuntime
from fastapi import WebSocket

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
RECONNECT_TIMEOUT_SECONDS = 120

PHASE_NAMES = {
    Phase.WAITING_FOR_PLAYERS: "waiting_for_players",
    Phase.OPENING_ATTACK: "opening_attack",
    Phase.DEFENSE: "defense",
    Phase.ATTACK_EXTENSION: "attack_extension",
    Phase.THROW_AFTER_TAKE: "throw_after_take",
    Phase.FINISHED: "finished",
}

SUIT_NAMES = {
    Suit.CLUBS: "clubs",
    Suit.DIAMONDS: "diamonds",
    Suit.HEARTS: "hearts",
    Suit.SPADES: "spades",
}

ACTION_NAMES = {
    ActionKind.ATTACK: "attack",
    ActionKind.DEFEND: "defend",
    ActionKind.TRANSFER: "transfer",
    ActionKind.TAKE: "take",
    ActionKind.PASS_ATTACK: "pass_attack",
}

SUIT_SYMBOLS = {
    "C": "♣",
    "D": "♦",
    "H": "♥",
    "S": "♠",
}


class RoomError(Exception):
    """Represent a stable room protocol error."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
    ) -> None:
        """Initialize an error safe to return to a client."""

        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass
class PlayerSeat:
    """Store one authenticated seat in a room."""

    player_id: str
    nickname: str
    token: str
    index: int
    is_bot: bool = False
    connections: set[WebSocket] = field(default_factory=set)
    disconnect_task: asyncio.Task[None] | None = None

    @property
    def connected(self) -> bool:
        """Return whether at least one browser owns the live seat."""

        return self.is_bot or bool(self.connections)


@dataclass
class GameRoom:
    """Store room membership and its authoritative engine instance."""

    room_id: str
    max_players: int
    players: list[PlayerSeat]
    created_at: str
    status: str = "waiting"
    engine: GameEngine | None = None
    seed: int | None = None
    technical_loser: str | None = None
    events: list[dict[str, str]] = field(default_factory=list)
    public_history: list[PublicAction] = field(default_factory=list)
    last_actor: int | None = None
    bot_random: Random = field(default_factory=Random)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    bot_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RoomService:
    """Coordinate room lifecycle, sockets, and engine commands."""

    def __init__(
        self,
        bot_runtime: FallbackBotRuntime | None = None,
        bot_move_delay_seconds: float = 0.0,
    ) -> None:
        """Initialize an empty process-local room registry."""

        self._rooms: dict[str, GameRoom] = {}
        self._bot_runtime = bot_runtime or FallbackBotRuntime(
            "models/bot_v1.onnx",
            "models/bot_v1_metadata.json",
        )
        self._bot_move_delay_seconds = max(
            0.0,
            bot_move_delay_seconds,
        )
        self._observation_builder = ObservationBuilder()
        self._heuristic_agent = HeuristicAgent()

    def bot_status(self) -> dict[str, Any]:
        """Return the inference backend selected at process startup."""

        return self._bot_runtime.status

    async def create_room(
        self,
        nickname: str,
        player_count: int,
        bot_count: int = 0,
    ) -> tuple[GameRoom, PlayerSeat]:
        """Create a private room and reserve its first seat."""

        clean_nickname = self._normalize_nickname(nickname)

        if player_count not in (2, 3):
            raise RoomError(
                "INVALID_PLAYER_COUNT",
                "В комнате может быть два или три игрока.",
            )
        if bot_count < 0 or bot_count >= player_count:
            raise RoomError(
                "INVALID_BOT_COUNT",
                "В комнате должен остаться хотя бы один человек.",
            )

        room_id = self._new_room_id()
        seat = self._new_seat(clean_nickname, index=0)
        bots = [
            self._new_bot_seat(index)
            for index in range(1, bot_count + 1)
        ]
        room = GameRoom(
            room_id=room_id,
            max_players=player_count,
            players=[seat, *bots],
            created_at=self._now(),
        )
        self._append_event(
            room,
            "system",
            f"{clean_nickname} создал комнату.",
        )
        for bot in bots:
            self._append_event(
                room,
                "join",
                f"{bot.nickname} занял место за столом.",
            )
        self._rooms[room_id] = room
        if len(room.players) == room.max_players:
            self._start_game(room)
            await self._advance_bots(room)
        return room, seat

    async def join_room(
        self,
        room_id: str,
        nickname: str,
    ) -> tuple[GameRoom, PlayerSeat]:
        """Join an available room and start the game when it is full."""

        room = self.get_room(room_id)
        clean_nickname = self._normalize_nickname(nickname)

        async with room.lock:
            if room.status != "waiting":
                raise RoomError(
                    "GAME_ALREADY_STARTED",
                    "Партия в этой комнате уже началась.",
                    status_code=409,
                )

            if len(room.players) >= room.max_players:
                raise RoomError(
                    "ROOM_IS_FULL",
                    "В комнате больше нет свободных мест.",
                    status_code=409,
                )

            if any(
                player.nickname.casefold() == clean_nickname.casefold()
                for player in room.players
            ):
                raise RoomError(
                    "NICKNAME_TAKEN",
                    "Выберите другое имя игрока.",
                    status_code=409,
                )

            seat = self._new_seat(
                clean_nickname,
                index=len(room.players),
            )
            room.players.append(seat)
            self._append_event(
                room,
                "join",
                f"{clean_nickname} присоединился к комнате.",
            )

            if len(room.players) == room.max_players:
                self._start_game(room)

        await self.broadcast(room)
        await self._advance_bots(room)
        return room, seat

    def get_room(self, room_id: str) -> GameRoom:
        """Return a room by its normalized invitation code."""

        normalized = room_id.strip().upper()
        room = self._rooms.get(normalized)

        if room is None:
            raise RoomError(
                "ROOM_NOT_FOUND",
                "Комната не найдена или уже закрыта.",
                status_code=404,
            )

        return room

    def authenticate(
        self,
        room: GameRoom,
        token: str,
    ) -> PlayerSeat:
        """Resolve a signed seat token inside one room."""

        for player in room.players:
            if secrets.compare_digest(player.token, token):
                return player

        raise RoomError(
            "INVALID_SEAT_TOKEN",
            "Не удалось подтвердить место игрока.",
            status_code=401,
        )

    def credentials(
        self,
        room: GameRoom,
        seat: PlayerSeat,
    ) -> dict[str, Any]:
        """Return browser credentials after create or join."""

        return {
            "roomId": room.room_id,
            "playerId": seat.player_id,
            "seatToken": seat.token,
            "maxPlayers": room.max_players,
            "botCount": sum(player.is_bot for player in room.players),
            "rulesVersion": str(RULES_VERSION),
        }

    def snapshot(
        self,
        room: GameRoom,
        viewer: PlayerSeat,
    ) -> dict[str, Any]:
        """Build a private state projection for one authenticated player."""

        players: list[dict[str, Any]] = []
        engine_state = room.engine.state if room.engine is not None else None

        for player in room.players:
            value: dict[str, Any] = {
                "id": player.player_id,
                "index": player.index,
                "nickname": player.nickname,
                "connected": player.connected,
                "isBot": player.is_bot,
                "isYou": player.player_id == viewer.player_id,
                "cardCount": 0,
                "placement": 0,
                "isDurak": False,
            }

            if engine_state is not None:
                state_player = engine_state["players"][player.index]
                value["cardCount"] = state_player["card_count"]
                value["placement"] = state_player["placement"]
                value["isDurak"] = state_player["is_durak"]

                if player.player_id == viewer.player_id:
                    value["hand"] = list(state_player["hand"])

            players.append(value)

        game = (
            self._game_snapshot(room, viewer)
            if engine_state is not None
            else None
        )

        return {
            "type": "snapshot",
            "room": {
                "id": room.room_id,
                "status": self._effective_status(room),
                "maxPlayers": room.max_players,
                "connectedPlayers": sum(
                    player.connected for player in room.players
                ),
                "reconnectTimeoutSeconds": RECONNECT_TIMEOUT_SECONDS,
                "createdAt": room.created_at,
            },
            "you": {
                "id": viewer.player_id,
                "index": viewer.index,
                "nickname": viewer.nickname,
            },
            "players": players,
            "game": game,
            "events": room.events[-30:],
            "rulesVersion": str(RULES_VERSION),
        }

    async def connect(
        self,
        room: GameRoom,
        seat: PlayerSeat,
        websocket: WebSocket,
    ) -> None:
        """Register a live browser and publish the new presence state."""

        await websocket.accept()
        seat.connections.add(websocket)

        if seat.disconnect_task is not None:
            seat.disconnect_task.cancel()
            seat.disconnect_task = None

        self._append_event(
            room,
            "connection",
            f"{seat.nickname} в сети.",
        )
        await self.broadcast(room)
        await self._advance_bots(room)

    async def disconnect(
        self,
        room: GameRoom,
        seat: PlayerSeat,
        websocket: WebSocket,
    ) -> None:
        """Remove a socket and start the reconnect countdown when needed."""

        seat.connections.discard(websocket)

        if (
            not seat.is_bot
            and not seat.connected
            and room.status == "playing"
            and seat.disconnect_task is None
        ):
            self._append_event(
                room,
                "connection",
                (
                    f"{seat.nickname} отключился. Партия поставлена "
                    "на паузу на 120 секунд."
                ),
            )
            seat.disconnect_task = asyncio.create_task(
                self._finish_after_disconnect(room, seat)
            )

        await self.broadcast(room)

    async def handle_message(
        self,
        room: GameRoom,
        seat: PlayerSeat,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> None:
        """Validate one WebSocket message and dispatch its command."""

        message_type = message.get("type")

        if message_type == "ping":
            await websocket.send_json({"type": "pong"})
            return

        if message_type != "action":
            raise RoomError(
                "UNKNOWN_MESSAGE",
                "Сервер не поддерживает такую команду.",
            )

        await self.apply_action(
            room,
            seat,
            message.get("expectedVersion"),
            message.get("action"),
        )

    async def apply_action(
        self,
        room: GameRoom,
        seat: PlayerSeat,
        expected_version: Any,
        payload: Any,
    ) -> None:
        """Apply one optimistic-concurrency game command."""

        async with room.lock:
            if room.status != "playing" or room.engine is None:
                raise RoomError(
                    "GAME_NOT_RUNNING",
                    "Партия ещё не началась или уже завершена.",
                    status_code=409,
                )

            if self._effective_status(room) == "paused":
                raise RoomError(
                    "GAME_PAUSED",
                    "Дождитесь возвращения отключившегося игрока.",
                    status_code=409,
                )

            state = room.engine.state

            if expected_version != state["version"]:
                raise RoomError(
                    "STALE_STATE",
                    "Состояние изменилось. Повторите действие.",
                    status_code=409,
                )

            action = self._parse_action(payload)
            action_phase = phase_name(state["phase"])

            try:
                room.engine.apply(seat.index, action)
            except GameError as error:
                raise RoomError(
                    "ILLEGAL_ACTION",
                    "Это действие сейчас недоступно.",
                    status_code=409,
                ) from error

            self._record_action(
                room,
                seat,
                action,
                action_phase,
            )

            if room.engine.state["phase"] == Phase.FINISHED:
                room.status = "finished"
                self._append_event(
                    room,
                    "system",
                    "Партия завершена.",
                )

        await self.broadcast(room)
        await self._advance_bots(room)

    async def broadcast(self, room: GameRoom) -> None:
        """Send a private snapshot to every connected seat."""

        for player in room.players:
            payload = self.snapshot(room, player)

            for websocket in tuple(player.connections):
                try:
                    await websocket.send_json(payload)
                except Exception:
                    player.connections.discard(websocket)

    def _start_game(self, room: GameRoom) -> None:
        """Create a deterministic engine when every seat is occupied."""

        room.seed = secrets.randbits(63)
        room.engine = GameEngine()
        room.engine.start(
            player_count=room.max_players,
            seed=room.seed,
            dealer=0,
        )
        room.public_history.clear()
        room.last_actor = None
        room.bot_random = Random(room.seed)
        room.status = "playing"
        self._append_event(
            room,
            "system",
            "Все игроки на месте. Партия началась.",
        )

    def _game_snapshot(
        self,
        room: GameRoom,
        viewer: PlayerSeat,
    ) -> dict[str, Any]:
        """Serialize the engine without exposing opponents' hands."""

        if room.engine is None:
            raise RuntimeError("Game snapshot requested before start")

        state = room.engine.state
        legal_actions = []

        if self._effective_status(room) == "playing":
            legal_actions = [
                self._serialize_action(action)
                for action in room.engine.legal_actions(viewer.index)
            ]

        return {
            "version": state["version"],
            "phase": PHASE_NAMES[state["phase"]],
            "dealer": state["dealer"],
            "mainAttacker": state["main_attacker"],
            "defender": state["defender"],
            "eligibleAttackers": state["eligible_attackers"],
            "passedAttackers": state["passed_attackers"],
            "attackCount": state["attack_count"],
            "attackLimit": state["attack_limit"],
            "deckCount": state["deck_count"],
            "discardCount": state["discard_count"],
            "trump": SUIT_NAMES[state["trump"]],
            "trumpCard": state["trump_card"],
            "transferLocked": state["transfer_locked"],
            "takeDeclared": state["take_declared"],
            "draw": state["draw"],
            "table": [
                {
                    "slot": value["slot"],
                    "attack": value["attack"],
                    "defense": value["defense"],
                }
                for value in state["table"]
            ],
            "legalActions": legal_actions,
            "technicalLoser": room.technical_loser,
        }

    async def _advance_bots(self, room: GameRoom) -> None:
        """Run scheduled bot turns until a human decision is required."""

        async with room.bot_lock:
            while room.status == "playing" and room.engine is not None:
                async with room.lock:
                    actor = self._next_actor(room)
                    if actor is None or not room.players[actor].is_bot:
                        return

                if self._bot_move_delay_seconds:
                    await asyncio.sleep(self._bot_move_delay_seconds)

                async with room.lock:
                    actor = self._next_actor(room)
                    if actor is None or not room.players[actor].is_bot:
                        return
                    if room.engine is None:
                        return

                    state = room.engine.state
                    native_actions = room.engine.legal_actions(actor)
                    observation = self._observation_builder.build(
                        state,
                        actor,
                        native_actions,
                        room.public_history,
                    )
                    action_index = self._bot_runtime.choose_action(
                        observation,
                        room.bot_random,
                    )
                    if (
                        action_index < 0
                        or action_index >= len(native_actions)
                    ):
                        action_index = self._heuristic_agent.choose_action(
                            observation,
                            room.bot_random,
                        )
                    action = native_actions[action_index]
                    action_phase = phase_name(state["phase"])
                    room.engine.apply(actor, action)
                    self._record_action(
                        room,
                        room.players[actor],
                        action,
                        action_phase,
                    )
                    if room.engine.state["phase"] == Phase.FINISHED:
                        room.status = "finished"
                        self._append_event(
                            room,
                            "system",
                            "Партия завершена.",
                        )

                await self.broadcast(room)

    def _next_actor(self, room: GameRoom) -> int | None:
        """Choose one legal actor with deterministic round-robin fairness."""

        if room.engine is None:
            return None
        state = room.engine.state
        if state["phase"] == Phase.FINISHED:
            return None
        player_count = int(state["player_count"])
        legal_players = {
            player
            for player in range(player_count)
            if room.engine.legal_actions(player)
        }
        if not legal_players:
            return None
        start = (
            int(state["main_attacker"])
            if room.last_actor is None
            else (room.last_actor + 1) % player_count
        )
        for offset in range(player_count):
            candidate = (start + offset) % player_count
            if candidate in legal_players:
                return candidate
        return None

    def _record_action(
        self,
        room: GameRoom,
        seat: PlayerSeat,
        action: Action,
        action_phase: str,
    ) -> None:
        """Append public replay data after a successful engine action."""

        room.public_history.append(
            PublicAction(
                actor=seat.index,
                phase=action_phase,
                action=action_from_native(action),
            )
        )
        room.public_history = room.public_history[-MAX_HISTORY:]
        room.last_actor = seat.index
        self._append_event(
            room,
            "action",
            self._describe_action(seat, action),
        )

    def _parse_action(self, payload: Any) -> Action:
        """Convert a JSON action into the bound C++ value object."""

        if not isinstance(payload, dict):
            raise RoomError(
                "INVALID_ACTION",
                "Команда должна содержать описание действия.",
            )

        kind = payload.get("kind")
        card = payload.get("card")
        target_slot = payload.get("targetSlot", 0)

        if kind == "attack" and isinstance(card, int):
            return Action.attack(card)

        if (
            kind == "defend"
            and isinstance(card, int)
            and isinstance(target_slot, int)
        ):
            return Action.defend(card, target_slot)

        if kind == "transfer" and isinstance(card, int):
            return Action.transfer(card)

        if kind == "take":
            return Action.take()

        if kind == "pass_attack":
            return Action.pass_attack()

        raise RoomError(
            "INVALID_ACTION",
            "Параметры игрового действия некорректны.",
        )

    def _serialize_action(self, action: Action) -> dict[str, Any]:
        """Serialize one legal engine action for a browser."""

        return {
            "kind": ACTION_NAMES[action.kind],
            "card": (
                action.card
                if action.kind
                in {
                    ActionKind.ATTACK,
                    ActionKind.DEFEND,
                    ActionKind.TRANSFER,
                }
                else None
            ),
            "targetSlot": (
                action.target_slot
                if action.kind == ActionKind.DEFEND
                else None
            ),
        }

    def _describe_action(
        self,
        seat: PlayerSeat,
        action: Action,
    ) -> str:
        """Create a concise public replay message."""

        if action.kind == ActionKind.TAKE:
            return f"{seat.nickname}: беру."

        if action.kind == ActionKind.PASS_ATTACK:
            return f"{seat.nickname}: бито / пас."

        label = self._card_label(action.card)

        if action.kind == ActionKind.ATTACK:
            return f"{seat.nickname} атакует {label}."

        if action.kind == ActionKind.DEFEND:
            return f"{seat.nickname} отбивает картой {label}."

        return f"{seat.nickname} переводит картой {label}."

    async def _finish_after_disconnect(
        self,
        room: GameRoom,
        seat: PlayerSeat,
    ) -> None:
        """Finish a game after the reconnect grace period expires."""

        current_task = asyncio.current_task()

        try:
            await asyncio.sleep(RECONNECT_TIMEOUT_SECONDS)

            async with room.lock:
                if seat.connected or room.status != "playing":
                    return

                room.status = "finished"
                room.technical_loser = seat.player_id
                self._append_event(
                    room,
                    "system",
                    (
                        f"{seat.nickname} не вернулся за 120 секунд "
                        "и получил техническое поражение."
                    ),
                )

            await self.broadcast(room)
        except asyncio.CancelledError:
            return
        finally:
            if seat.disconnect_task is current_task:
                seat.disconnect_task = None

    def _effective_status(self, room: GameRoom) -> str:
        """Return the client-visible room state."""

        if room.status != "playing":
            return room.status

        if not all(player.connected for player in room.players):
            return "paused"

        return "playing"

    def _new_room_id(self) -> str:
        """Generate a collision-resistant human-readable room code."""

        while True:
            value = "".join(
                secrets.choice(ROOM_ALPHABET) for _ in range(6)
            )

            if value not in self._rooms:
                return value

    @staticmethod
    def _new_seat(nickname: str, index: int) -> PlayerSeat:
        """Create credentials for one room seat."""

        return PlayerSeat(
            player_id=secrets.token_hex(8),
            nickname=nickname,
            token=secrets.token_urlsafe(32),
            index=index,
        )

    @staticmethod
    def _new_bot_seat(index: int) -> PlayerSeat:
        """Create one internal AI-controlled room seat."""

        return PlayerSeat(
            player_id=secrets.token_hex(8),
            nickname=f"AI {index}",
            token=secrets.token_urlsafe(32),
            index=index,
            is_bot=True,
        )

    @staticmethod
    def _normalize_nickname(nickname: str) -> str:
        """Validate and normalize a public nickname."""

        value = " ".join(nickname.strip().split())

        if len(value) < 2 or len(value) > 24:
            raise RoomError(
                "INVALID_NICKNAME",
                "Имя должно содержать от 2 до 24 символов.",
            )

        return value

    @staticmethod
    def _append_event(
        room: GameRoom,
        kind: str,
        message: str,
    ) -> None:
        """Append one bounded public activity event."""

        room.events.append(
            {
                "id": secrets.token_hex(6),
                "kind": kind,
                "message": message,
                "at": RoomService._now(),
            }
        )

        if len(room.events) > 200:
            del room.events[:-200]

    @staticmethod
    def _card_label(card: int) -> str:
        """Convert the compact C++ label to a Unicode card label."""

        value = card_name(card)
        return f"{value[:-1]}{SUIT_SYMBOLS[value[-1]]}"

    @staticmethod
    def _now() -> str:
        """Return a stable UTC timestamp."""

        return datetime.now(UTC).isoformat()
