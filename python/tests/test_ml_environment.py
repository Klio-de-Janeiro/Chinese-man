"""Tests for leak-free deterministic self-play."""

from __future__ import annotations

from chinese_durak.ml import (
    ChineseDurakEnv,
    FeatureEncoder,
    HeuristicAgent,
)
from chinese_durak.ml.constants import (
    GLOBAL_FEATURE_DIM,
    MAX_HAND_SIZE,
    MAX_HISTORY,
    MAX_TABLE_CARDS,
)
from chinese_durak.ml.simulation import play_episode


def test_observation_contains_only_own_hand() -> None:
    """Expose opponent counts without exposing opponent cards."""

    environment = ChineseDurakEnv()
    observation = environment.reset(seed=41, player_count=3)
    payload = observation.to_dict()

    assert payload["own_hand"] == list(observation.own_hand)
    assert len(payload["player_card_counts"]) == 3
    assert "players" not in payload
    assert "deck" not in payload


def test_feature_shapes_are_stable() -> None:
    """Keep the serialized encoder dimensions backward compatible."""

    observation = ChineseDurakEnv().reset(seed=42, player_count=2)
    encoded = FeatureEncoder().encode(observation)

    assert len(encoded.hand_cards) == MAX_HAND_SIZE
    assert len(encoded.table_cards) == MAX_TABLE_CARDS
    assert len(encoded.table_zones) == MAX_TABLE_CARDS
    assert len(encoded.history) == MAX_HISTORY
    assert len(encoded.global_features) == GLOBAL_FEATURE_DIM
    assert len(encoded.actions) == len(observation.legal_actions)


def test_heuristic_episode_is_deterministic() -> None:
    """Reproduce rewards and decision counts from an identical seed."""

    agents = [HeuristicAgent(), HeuristicAgent(), HeuristicAgent()]
    first = play_episode(agents, seed=8128, player_count=3)
    second = play_episode(agents, seed=8128, player_count=3)

    assert first.rewards == second.rewards
    assert first.decision_count == second.decision_count
    assert [
        decision.chosen_action_index for decision in first.decisions
    ] == [
        decision.chosen_action_index for decision in second.decisions
    ]


def test_legal_self_play_terminates() -> None:
    """Finish representative two- and three-player games legally."""

    for player_count in (2, 3):
        for seed in range(12):
            trace = play_episode(
                [HeuristicAgent() for _ in range(player_count)],
                seed=10_000 + seed,
                player_count=player_count,
                collect_decisions=False,
            )
            assert len(trace.rewards) == player_count
            assert trace.decision_count > 0
