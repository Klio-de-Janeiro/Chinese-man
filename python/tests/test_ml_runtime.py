"""Tests for safe production inference fallback."""

from __future__ import annotations

from random import Random

from chinese_durak.ml.environment import ChineseDurakEnv
from chinese_durak.ml.runtime import FallbackBotRuntime


def test_missing_release_model_uses_legal_heuristic_action(
    tmp_path,
) -> None:
    """Keep AI rooms playable before trained weights are installed."""

    runtime = FallbackBotRuntime(
        tmp_path / "missing.onnx",
        tmp_path / "missing.json",
    )
    observation = ChineseDurakEnv().reset(seed=99, player_count=2)
    action_index = runtime.choose_action(observation, Random(99))

    assert runtime.status["backend"] == "heuristic"
    assert 0 <= action_index < len(observation.legal_actions)
