"""PyTorch policy agent used during PPO and evaluation."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

from ..batching import encode_batch
from ..contracts import PlayerObservation
from ..tensors import to_torch_inputs

if TYPE_CHECKING:
    from torch import nn


class TorchPolicyAgent:
    """Choose actions from a PolicyValueNetwork."""

    name = "policy-value"

    def __init__(
        self,
        model: nn.Module,
        device: str,
        deterministic: bool = False,
        temperature: float = 1.0,
    ) -> None:
        """Store an evaluation model and action-selection settings."""

        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.model = model
        self.device = device
        self.deterministic = deterministic
        self.temperature = temperature

    def choose_action(
        self,
        observation: PlayerObservation,
        random: Random,
    ) -> int:
        """Return a legal index sampled from masked policy logits."""

        import torch

        del random
        inputs = to_torch_inputs(
            encode_batch([observation]),
            self.device,
        )
        with torch.inference_mode():
            logits, _ = self.model(**inputs)
            logits = logits[0, : len(observation.legal_actions)]
            if self.deterministic:
                return int(logits.argmax().item())

            distribution = torch.distributions.Categorical(
                logits=logits / self.temperature
            )
            return int(distribution.sample().item())
