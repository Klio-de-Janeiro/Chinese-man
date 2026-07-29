"""NumPy batching shared by PyTorch training and ONNX inference."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .constants import (
    GLOBAL_FEATURE_DIM,
    MAX_HAND_SIZE,
    MAX_HISTORY,
    MAX_TABLE_CARDS,
)
from .contracts import PlayerObservation
from .observation import FeatureEncoder


@dataclass(frozen=True)
class NumpyBatch:
    """Hold one padded batch accepted by PolicyValueNetwork."""

    hand_cards: np.ndarray
    table_cards: np.ndarray
    table_zones: np.ndarray
    history: np.ndarray
    history_lengths: np.ndarray
    global_features: np.ndarray
    actions: np.ndarray
    action_mask: np.ndarray
    trump_suit: np.ndarray

    def to_dict(self) -> dict[str, np.ndarray]:
        """Return inputs keyed by exported model input names."""

        return {
            "hand_cards": self.hand_cards,
            "table_cards": self.table_cards,
            "table_zones": self.table_zones,
            "history": self.history,
            "history_lengths": self.history_lengths,
            "global_features": self.global_features,
            "actions": self.actions,
            "action_mask": self.action_mask,
            "trump_suit": self.trump_suit,
        }


def encode_batch(
    observations: Sequence[PlayerObservation],
) -> NumpyBatch:
    """Encode and pad a non-empty observation batch."""

    if not observations:
        raise ValueError("Cannot encode an empty observation batch")

    encoder = FeatureEncoder()
    encoded = [encoder.encode(observation) for observation in observations]
    batch_size = len(encoded)
    max_actions = max(len(state.actions) for state in encoded)
    hand_cards = np.zeros(
        (batch_size, MAX_HAND_SIZE),
        dtype=np.int64,
    )
    table_cards = np.zeros(
        (batch_size, MAX_TABLE_CARDS),
        dtype=np.int64,
    )
    table_zones = np.zeros_like(table_cards)
    history = np.zeros(
        (batch_size, MAX_HISTORY, 5),
        dtype=np.int64,
    )
    history_lengths = np.zeros(batch_size, dtype=np.int64)
    global_features = np.zeros(
        (batch_size, GLOBAL_FEATURE_DIM),
        dtype=np.float32,
    )
    actions = np.zeros(
        (batch_size, max_actions, 3),
        dtype=np.int64,
    )
    action_mask = np.zeros(
        (batch_size, max_actions),
        dtype=np.bool_,
    )
    trump_suit = np.zeros(batch_size, dtype=np.int64)

    for index, state in enumerate(encoded):
        hand_cards[index] = state.hand_cards
        table_cards[index] = state.table_cards
        table_zones[index] = state.table_zones
        history[index] = state.history
        history_lengths[index] = state.history_length
        global_features[index] = state.global_features
        action_count = len(state.actions)
        actions[index, :action_count] = state.actions
        action_mask[index, :action_count] = True
        trump_suit[index] = state.trump_suit

    return NumpyBatch(
        hand_cards=hand_cards,
        table_cards=table_cards,
        table_zones=table_zones,
        history=history,
        history_lengths=history_lengths,
        global_features=global_features,
        actions=actions,
        action_mask=action_mask,
        trump_suit=trump_suit,
    )
