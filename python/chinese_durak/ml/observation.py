"""Private observation construction and deterministic feature encoding."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from chinese_durak import RULES_VERSION

from .constants import (
    ACTION_KIND_TO_ID,
    DECK_SIZE,
    GLOBAL_FEATURE_DIM,
    MAX_HAND_SIZE,
    MAX_HISTORY,
    MAX_PLAYERS,
    MAX_TABLE_CARDS,
    MAX_TABLE_SLOTS,
    PHASE_TO_ID,
)
from .contracts import (
    ActionView,
    PlayerObservation,
    PublicAction,
    TableSlotView,
)
from .native import action_from_native, phase_name, suit_index


@dataclass(frozen=True)
class EncodedState:
    """Contain fixed-size model inputs except the legal action axis."""

    hand_cards: tuple[int, ...]
    table_cards: tuple[int, ...]
    table_zones: tuple[int, ...]
    history: tuple[tuple[int, int, int, int, int], ...]
    history_length: int
    global_features: tuple[float, ...]
    actions: tuple[tuple[int, int, int], ...]
    trump_suit: int


class ObservationBuilder:
    """Build leak-free observations from a server-side engine snapshot."""

    def build(
        self,
        state: dict[str, Any],
        viewer: int,
        legal_actions: Sequence[Any],
        history: Sequence[PublicAction],
    ) -> PlayerObservation:
        """Project full server state into one player's information set."""

        player_count = int(state["player_count"])

        if viewer < 0 or viewer >= player_count:
            raise ValueError("Viewer must be an active seat index")

        players = state["players"]
        own_player = players[viewer]

        return PlayerObservation(
            rules_version=str(RULES_VERSION),
            viewer=viewer,
            player_count=player_count,
            phase=phase_name(state["phase"]),
            decision_index=int(
                state.get("decision_count", state["version"] - 1)
            ),
            dealer=int(state["dealer"]),
            main_attacker=int(state["main_attacker"]),
            defender=int(state["defender"]),
            eligible_attackers=int(state["eligible_attackers"]),
            passed_attackers=int(state["passed_attackers"]),
            attack_count=int(state["attack_count"]),
            attack_limit=int(state["attack_limit"]),
            deck_count=int(state["deck_count"]),
            discard_count=int(state["discard_count"]),
            trump_suit=suit_index(state["trump"]),
            trump_card=int(state["trump_card"]),
            transfer_locked=bool(state["transfer_locked"]),
            take_declared=bool(state["take_declared"]),
            draw=bool(state["draw"]),
            own_hand=tuple(int(card) for card in own_player["hand"]),
            player_card_counts=tuple(
                int(player["card_count"]) for player in players
            ),
            player_active=tuple(
                bool(player["active"]) for player in players
            ),
            player_placements=tuple(
                int(player["placement"]) for player in players
            ),
            player_is_durak=tuple(
                bool(player["is_durak"]) for player in players
            ),
            table=tuple(
                TableSlotView(
                    slot=int(slot["slot"]),
                    attack=int(slot["attack"]),
                    defense=(
                        int(slot["defense"])
                        if slot["defense"] is not None
                        else None
                    ),
                )
                for slot in state["table"]
            ),
            history=tuple(history[-MAX_HISTORY:]),
            legal_actions=tuple(
                action_from_native(action) for action in legal_actions
            ),
        )


class FeatureEncoder:
    """Encode a PlayerObservation with seat-rotation symmetry."""

    def encode(self, observation: PlayerObservation) -> EncodedState:
        """Return stable integer tokens and normalized global features."""

        hand = tuple(card + 1 for card in observation.own_hand)
        hand_cards = self._pad(hand, MAX_HAND_SIZE)
        table_cards, table_zones = self._encode_table(observation)
        history = self._encode_history(observation)
        actions = tuple(
            self.encode_action(action)
            for action in observation.legal_actions
        )

        if not actions:
            raise ValueError("A decision observation needs legal actions")

        global_features = self._global_features(observation)

        if len(global_features) != GLOBAL_FEATURE_DIM:
            raise RuntimeError("Global feature contract has changed")

        return EncodedState(
            hand_cards=hand_cards,
            table_cards=table_cards,
            table_zones=table_zones,
            history=history,
            history_length=min(len(observation.history), MAX_HISTORY),
            global_features=global_features,
            actions=actions,
            trump_suit=observation.trump_suit,
        )

    @staticmethod
    def encode_action(action: ActionView) -> tuple[int, int, int]:
        """Encode one legal action using zero as the padding token."""

        try:
            kind = ACTION_KIND_TO_ID[action.kind] + 1
        except KeyError as error:
            raise ValueError(
                f"Unknown action kind: {action.kind}"
            ) from error

        return (
            kind,
            action.card + 1 if action.card is not None else 0,
            (
                action.target_slot + 1
                if action.target_slot is not None
                else 0
            ),
        )

    def _encode_table(
        self,
        observation: PlayerObservation,
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """Place attack and defense cards into fixed slot positions."""

        cards = [0] * MAX_TABLE_CARDS
        zones = [0] * MAX_TABLE_CARDS

        for slot in observation.table:
            attack_index = slot.slot * 2
            defense_index = attack_index + 1
            cards[attack_index] = slot.attack + 1
            zones[attack_index] = 2

            if slot.defense is not None:
                cards[defense_index] = slot.defense + 1
                zones[defense_index] = 3

        return tuple(cards), tuple(zones)

    def _encode_history(
        self,
        observation: PlayerObservation,
    ) -> tuple[tuple[int, int, int, int, int], ...]:
        """Encode chronological public actions and append padding."""

        encoded: list[tuple[int, int, int, int, int]] = []

        for event in observation.history[-MAX_HISTORY:]:
            actor = self._relative_index(
                event.actor,
                observation.viewer,
                observation.player_count,
            )
            encoded.append(
                (
                    actor + 1,
                    ACTION_KIND_TO_ID[event.action.kind] + 1,
                    (
                        event.action.card + 1
                        if event.action.card is not None
                        else 0
                    ),
                    (
                        event.action.target_slot + 1
                        if event.action.target_slot is not None
                        else 0
                    ),
                    PHASE_TO_ID[event.phase] + 1,
                )
            )

        padding = [(0, 0, 0, 0, 0)] * (
            MAX_HISTORY - len(encoded)
        )
        return tuple(encoded + padding)

    def _global_features(
        self,
        observation: PlayerObservation,
    ) -> tuple[float, ...]:
        """Build the normalized 44-value global vector."""

        features: list[float] = []
        phase = PHASE_TO_ID[observation.phase]

        features.extend(self._one_hot(phase, 6))
        features.extend(
            (
                float(observation.player_count == 2),
                float(observation.player_count == 3),
            )
        )

        if observation.viewer == observation.main_attacker:
            role = 0
        elif observation.viewer == observation.defender:
            role = 1
        else:
            role = 2

        features.extend(self._one_hot(role, 3))
        features.extend(
            (
                observation.deck_count / DECK_SIZE,
                observation.discard_count / DECK_SIZE,
                len(observation.own_hand) / DECK_SIZE,
            )
        )
        relative_counts = self._relative_values(
            observation.player_card_counts,
            observation,
            pad=0,
        )
        features.extend(count / DECK_SIZE for count in relative_counts)
        relative_active = self._relative_values(
            observation.player_active,
            observation,
            pad=False,
        )
        features.extend(float(active) for active in relative_active)
        relative_placements = self._relative_values(
            observation.player_placements,
            observation,
            pad=0,
        )
        features.extend(
            place / MAX_PLAYERS for place in relative_placements
        )
        features.extend(
            self._relative_mask(
                observation.eligible_attackers,
                observation,
            )
        )
        features.extend(
            self._relative_mask(
                observation.passed_attackers,
                observation,
            )
        )
        features.extend(
            (
                observation.attack_count / MAX_TABLE_SLOTS,
                observation.attack_limit / MAX_TABLE_SLOTS,
            )
        )
        features.extend(
            self._relative_player_one_hot(
                observation.dealer,
                observation,
            )
        )
        features.extend(
            self._relative_player_one_hot(
                observation.main_attacker,
                observation,
            )
        )
        features.extend(
            self._relative_player_one_hot(
                observation.defender,
                observation,
            )
        )
        features.extend(
            (
                float(observation.transfer_locked),
                float(observation.take_declared),
                float(observation.draw),
                (
                    sum(slot.defense is not None for slot in observation.table)
                    / MAX_TABLE_SLOTS
                ),
            )
        )
        return tuple(features)

    def _relative_values(
        self,
        values: Sequence[Any],
        observation: PlayerObservation,
        pad: Any,
    ) -> tuple[Any, ...]:
        """Rotate per-player values so the viewer is always first."""

        result = []
        for relative in range(MAX_PLAYERS):
            if relative >= observation.player_count:
                result.append(pad)
                continue

            absolute = (
                observation.viewer + relative
            ) % observation.player_count
            result.append(values[absolute])

        return tuple(result)

    def _relative_mask(
        self,
        mask: int,
        observation: PlayerObservation,
    ) -> tuple[float, ...]:
        """Rotate an absolute player bit mask into viewer coordinates."""

        values = []
        for relative in range(MAX_PLAYERS):
            if relative >= observation.player_count:
                values.append(0.0)
                continue

            absolute = (
                observation.viewer + relative
            ) % observation.player_count
            values.append(float(bool(mask & (1 << absolute))))

        return tuple(values)

    def _relative_player_one_hot(
        self,
        player: int,
        observation: PlayerObservation,
    ) -> tuple[float, ...]:
        """Encode one absolute player in viewer-relative coordinates."""

        if player < 0 or player >= observation.player_count:
            return (0.0,) * MAX_PLAYERS

        relative = self._relative_index(
            player,
            observation.viewer,
            observation.player_count,
        )
        return self._one_hot(relative, MAX_PLAYERS)

    @staticmethod
    def _relative_index(
        player: int,
        viewer: int,
        player_count: int,
    ) -> int:
        """Return a circular seat offset from the viewer."""

        return (player - viewer) % player_count

    @staticmethod
    def _one_hot(index: int, size: int) -> tuple[float, ...]:
        """Return one immutable one-hot vector."""

        return tuple(float(position == index) for position in range(size))

    @staticmethod
    def _pad(values: Sequence[int], size: int) -> tuple[int, ...]:
        """Right-pad an integer sequence with zero tokens."""

        if len(values) > size:
            raise ValueError("Feature sequence exceeds its schema limit")

        return tuple(values) + (0,) * (size - len(values))
