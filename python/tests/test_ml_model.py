"""Optional tensor-contract checks for the policy-value model."""

from __future__ import annotations

import importlib.util

import pytest

torch_available = importlib.util.find_spec("torch") is not None
pytestmark = pytest.mark.skipif(
    not torch_available,
    reason="PyTorch is an optional ML dependency",
)


def test_policy_masks_padding_and_returns_values() -> None:
    """Preserve dynamic legal-action axes and value shapes."""

    import torch
    from chinese_durak.ml.batching import encode_batch
    from chinese_durak.ml.environment import ChineseDurakEnv
    from chinese_durak.ml.models import ModelConfig, PolicyValueNetwork
    from chinese_durak.ml.tensors import to_torch_inputs

    environment = ChineseDurakEnv()
    first = environment.reset(seed=1, player_count=2)
    second = ChineseDurakEnv().reset(seed=2, player_count=3)
    batch = to_torch_inputs(encode_batch([first, second]))
    model = PolicyValueNetwork(
        ModelConfig(
            card_dim=16,
            history_dim=16,
            action_dim=24,
            hidden_dim=32,
            dropout=0.0,
        )
    )
    model.eval()

    with torch.inference_mode():
        logits, values = model(**batch)

    assert logits.shape[0] == 2
    assert values.shape == (2,)
    assert torch.all(logits[~batch["action_mask"]] < -1.0e8)
