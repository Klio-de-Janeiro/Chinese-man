"""Serializable contracts for private observations and trajectories."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .constants import ENCODER_VERSION, ML_SCHEMA_VERSION


@dataclass(frozen=True)
class ActionView:
    """Describe one action already approved by the game engine."""

    kind: str
    card: int | None = None
    target_slot: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ActionView:
        """Restore an action from a serialized record."""

        return cls(
            kind=str(value["kind"]),
            card=(
                int(value["card"])
                if value.get("card") is not None
                else None
            ),
            target_slot=(
                int(value["target_slot"])
                if value.get("target_slot") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class TableSlotView:
    """Store the public cards in one table slot."""

    slot: int
    attack: int
    defense: int | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TableSlotView:
        """Restore a table slot from a serialized record."""

        return cls(
            slot=int(value["slot"]),
            attack=int(value["attack"]),
            defense=(
                int(value["defense"])
                if value.get("defense") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class PublicAction:
    """Record one action visible to every player."""

    actor: int
    phase: str
    action: ActionView

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return {
            "actor": self.actor,
            "phase": self.phase,
            "action": self.action.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PublicAction:
        """Restore a public action from a serialized record."""

        return cls(
            actor=int(value["actor"]),
            phase=str(value["phase"]),
            action=ActionView.from_dict(value["action"]),
        )


@dataclass(frozen=True)
class PlayerObservation:
    """Contain only information available to one acting player."""

    rules_version: str
    viewer: int
    player_count: int
    phase: str
    decision_index: int
    dealer: int
    main_attacker: int
    defender: int
    eligible_attackers: int
    passed_attackers: int
    attack_count: int
    attack_limit: int
    deck_count: int
    discard_count: int
    trump_suit: int
    trump_card: int
    transfer_locked: bool
    take_declared: bool
    draw: bool
    own_hand: tuple[int, ...]
    player_card_counts: tuple[int, ...]
    player_active: tuple[bool, ...]
    player_placements: tuple[int, ...]
    player_is_durak: tuple[bool, ...]
    table: tuple[TableSlotView, ...]
    history: tuple[PublicAction, ...]
    legal_actions: tuple[ActionView, ...]
    schema_version: str = ML_SCHEMA_VERSION
    encoder_version: str = ENCODER_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return {
            "schema_version": self.schema_version,
            "encoder_version": self.encoder_version,
            "rules_version": self.rules_version,
            "viewer": self.viewer,
            "player_count": self.player_count,
            "phase": self.phase,
            "decision_index": self.decision_index,
            "dealer": self.dealer,
            "main_attacker": self.main_attacker,
            "defender": self.defender,
            "eligible_attackers": self.eligible_attackers,
            "passed_attackers": self.passed_attackers,
            "attack_count": self.attack_count,
            "attack_limit": self.attack_limit,
            "deck_count": self.deck_count,
            "discard_count": self.discard_count,
            "trump_suit": self.trump_suit,
            "trump_card": self.trump_card,
            "transfer_locked": self.transfer_locked,
            "take_declared": self.take_declared,
            "draw": self.draw,
            "own_hand": list(self.own_hand),
            "player_card_counts": list(self.player_card_counts),
            "player_active": list(self.player_active),
            "player_placements": list(self.player_placements),
            "player_is_durak": list(self.player_is_durak),
            "table": [slot.to_dict() for slot in self.table],
            "history": [event.to_dict() for event in self.history],
            "legal_actions": [
                action.to_dict() for action in self.legal_actions
            ],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PlayerObservation:
        """Restore an observation from a dataset record."""

        return cls(
            schema_version=str(value["schema_version"]),
            encoder_version=str(value["encoder_version"]),
            rules_version=str(value["rules_version"]),
            viewer=int(value["viewer"]),
            player_count=int(value["player_count"]),
            phase=str(value["phase"]),
            decision_index=int(value["decision_index"]),
            dealer=int(value["dealer"]),
            main_attacker=int(value["main_attacker"]),
            defender=int(value["defender"]),
            eligible_attackers=int(value["eligible_attackers"]),
            passed_attackers=int(value["passed_attackers"]),
            attack_count=int(value["attack_count"]),
            attack_limit=int(value["attack_limit"]),
            deck_count=int(value["deck_count"]),
            discard_count=int(value["discard_count"]),
            trump_suit=int(value["trump_suit"]),
            trump_card=int(value["trump_card"]),
            transfer_locked=bool(value["transfer_locked"]),
            take_declared=bool(value["take_declared"]),
            draw=bool(value["draw"]),
            own_hand=tuple(int(card) for card in value["own_hand"]),
            player_card_counts=tuple(
                int(count) for count in value["player_card_counts"]
            ),
            player_active=tuple(
                bool(active) for active in value["player_active"]
            ),
            player_placements=tuple(
                int(place) for place in value["player_placements"]
            ),
            player_is_durak=tuple(
                bool(is_durak) for is_durak in value["player_is_durak"]
            ),
            table=tuple(
                TableSlotView.from_dict(slot) for slot in value["table"]
            ),
            history=tuple(
                PublicAction.from_dict(event) for event in value["history"]
            ),
            legal_actions=tuple(
                ActionView.from_dict(action)
                for action in value["legal_actions"]
            ),
        )


@dataclass(frozen=True)
class DecisionSample:
    """Store one supervised or on-policy decision."""

    seed: int
    player_count: int
    episode_id: str
    observation: PlayerObservation
    chosen_action_index: int
    teacher: str
    outcome: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return a dataset-ready representation."""

        return {
            "schema_version": ML_SCHEMA_VERSION,
            "rules_version": self.observation.rules_version,
            "seed": self.seed,
            "player_count": self.player_count,
            "episode_id": self.episode_id,
            "decision_index": self.observation.decision_index,
            "actor": self.observation.viewer,
            "observation": self.observation.to_dict(),
            "chosen_action_index": self.chosen_action_index,
            "teacher": self.teacher,
            "outcome": self.outcome,
        }
