"""Direct pybind11 self-play environment without network or database calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chinese_durak import GameEngine, Phase

from .constants import MAX_HISTORY
from .contracts import PlayerObservation, PublicAction
from .native import action_to_native, phase_name
from .observation import ObservationBuilder


@dataclass(frozen=True)
class EnvironmentStep:
    """Describe the state after one authoritative engine decision."""

    observation: PlayerObservation | None
    terminated: bool
    rewards: tuple[float, ...] | None


class ChineseDurakEnv:
    """Expose deterministic turn-by-turn self-play over GameEngine."""

    def __init__(self) -> None:
        """Initialize an environment that has not been reset."""

        self._engine: GameEngine | None = None
        self._builder = ObservationBuilder()
        self._history: list[PublicAction] = []
        self._last_actor: int | None = None
        self._seed = 0

    @property
    def state(self) -> dict[str, Any]:
        """Return the native snapshot for diagnostics and final results."""

        if self._engine is None:
            raise RuntimeError("Environment has not been reset")
        return self._engine.state

    @property
    def seed(self) -> int:
        """Return the deterministic episode seed."""

        return self._seed

    def reset(
        self,
        seed: int,
        player_count: int = 2,
        dealer: int = 0,
    ) -> PlayerObservation:
        """Start one deterministic game and return its first decision."""

        self._engine = GameEngine()
        self._engine.start(
            player_count=player_count,
            seed=seed,
            dealer=dealer,
        )
        self._history = []
        self._last_actor = None
        self._seed = seed
        return self.observation()

    def current_actor(self) -> int:
        """Select one legal actor with deterministic round-robin fairness."""

        if self._engine is None:
            raise RuntimeError("Environment has not been reset")

        if self.state["phase"] == Phase.FINISHED:
            raise RuntimeError("A finished environment has no actor")

        legal_players = [
            player
            for player in range(int(self.state["player_count"]))
            if self._engine.legal_actions(player)
        ]
        if not legal_players:
            raise RuntimeError("Non-terminal state has no legal actor")

        start = (
            int(self.state["main_attacker"])
            if self._last_actor is None
            else (
                self._last_actor + 1
            ) % int(self.state["player_count"])
        )
        for offset in range(int(self.state["player_count"])):
            candidate = (
                start + offset
            ) % int(self.state["player_count"])
            if candidate in legal_players:
                return candidate

        raise RuntimeError("Unable to schedule a legal actor")

    def observation(self) -> PlayerObservation:
        """Build the current actor's leak-free PlayerView."""

        if self._engine is None:
            raise RuntimeError("Environment has not been reset")

        actor = self.current_actor()
        legal_actions = self._engine.legal_actions(actor)
        return self._builder.build(
            self.state,
            actor,
            legal_actions,
            self._history,
        )

    def step(self, action_index: int) -> EnvironmentStep:
        """Apply one indexed legal action and return the next decision."""

        if self._engine is None:
            raise RuntimeError("Environment has not been reset")

        actor = self.current_actor()
        legal_actions = self._engine.legal_actions(actor)
        if action_index < 0 or action_index >= len(legal_actions):
            raise ValueError("Action index is outside legal_actions")

        observation = self._builder.build(
            self.state,
            actor,
            legal_actions,
            self._history,
        )
        action = observation.legal_actions[action_index]
        event = PublicAction(
            actor=actor,
            phase=phase_name(self.state["phase"]),
            action=action,
        )
        self._engine.apply(actor, action_to_native(action))
        self._history.append(event)
        self._history = self._history[-MAX_HISTORY:]
        self._last_actor = actor

        if self.state["phase"] == Phase.FINISHED:
            return EnvironmentStep(
                observation=None,
                terminated=True,
                rewards=self.terminal_rewards(),
            )

        return EnvironmentStep(
            observation=self.observation(),
            terminated=False,
            rewards=None,
        )

    def terminal_rewards(self) -> tuple[float, ...]:
        """Map final places to +1, 0, and -1 player rewards."""

        if self.state["phase"] != Phase.FINISHED:
            raise RuntimeError("Rewards exist only after termination")
        if bool(self.state["draw"]):
            return (0.0,) * int(self.state["player_count"])

        rewards = []
        for player in self.state["players"]:
            if bool(player["is_durak"]):
                rewards.append(-1.0)
            elif int(player["placement"]) == 1:
                rewards.append(1.0)
            else:
                rewards.append(0.0)
        return tuple(rewards)
