"""Imitation and reinforcement-learning trainers."""

from .imitation import ImitationConfig, train_imitation
from .ppo import PPOConfig, train_ppo

__all__ = [
    "ImitationConfig",
    "PPOConfig",
    "train_imitation",
    "train_ppo",
]
