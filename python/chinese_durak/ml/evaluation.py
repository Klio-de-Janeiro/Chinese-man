"""Reproducible cross-play evaluation for policy checkpoints."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .agents import (
    Agent,
    GreedyAgent,
    HeuristicAgent,
    RandomAgent,
    TorchPolicyAgent,
)
from .simulation import play_episode
from .training.checkpoints import load_checkpoint


@dataclass(frozen=True)
class EvaluationConfig:
    """Configure paired-seed evaluation against reference agents."""

    checkpoint: str
    output_path: str
    seed: int = 50_000
    games_per_seat: int = 1_000
    player_counts: tuple[int, ...] = (2, 3)
    deterministic: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EvaluationConfig:
        """Build configuration while normalizing sequence fields."""

        payload = dict(value)
        payload["player_counts"] = tuple(
            payload.get("player_counts", (2, 3))
        )
        return cls(**payload)

    def validate(self) -> None:
        """Reject invalid evaluation settings."""

        if self.games_per_seat <= 0:
            raise ValueError("games_per_seat must be positive")
        if not self.player_counts:
            raise ValueError("player_counts cannot be empty")
        if any(count not in (2, 3) for count in self.player_counts):
            raise ValueError("player_counts may contain only 2 and 3")


def _reference_agents() -> dict[str, type[Agent]]:
    """Return the stable baseline roster."""

    return {
        "random": RandomAgent,
        "greedy": GreedyAgent,
        "heuristic": HeuristicAgent,
    }


def _evaluate_matchup(
    policy: TorchPolicyAgent,
    baseline_type: type[Agent],
    player_count: int,
    games_per_seat: int,
    start_seed: int,
) -> dict[str, float]:
    """Evaluate every policy seat with identical seed sets."""

    rewards = []
    first_places = 0
    last_places = 0
    decisions = []
    for policy_seat in range(player_count):
        for offset in range(games_per_seat):
            agents: list[Agent] = [
                baseline_type() for _ in range(player_count)
            ]
            agents[policy_seat] = policy
            trace = play_episode(
                agents=agents,
                seed=start_seed + offset,
                player_count=player_count,
                collect_decisions=False,
            )
            reward = trace.rewards[policy_seat]
            rewards.append(reward)
            first_places += int(reward == 1.0)
            last_places += int(reward == -1.0)
            decisions.append(trace.decision_count)

    game_count = len(rewards)
    return {
        "games": float(game_count),
        "mean_reward": float(np.mean(rewards)),
        "first_place_rate": first_places / game_count,
        "last_place_rate": last_places / game_count,
        "mean_decisions": float(np.mean(decisions)),
    }


def evaluate_checkpoint(
    config: EvaluationConfig,
) -> dict[str, Any]:
    """Evaluate one checkpoint and write a self-contained JSON report."""

    config.validate()
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, checkpoint = load_checkpoint(config.checkpoint, device)
    model.eval()
    policy = TorchPolicyAgent(
        model=model,
        device=device,
        deterministic=config.deterministic,
    )
    matchups: dict[str, dict[str, float]] = {}
    for baseline_name, baseline_type in _reference_agents().items():
        for player_count in config.player_counts:
            key = f"{player_count}p_vs_{baseline_name}"
            matchups[key] = _evaluate_matchup(
                policy=policy,
                baseline_type=baseline_type,
                player_count=player_count,
                games_per_seat=config.games_per_seat,
                start_seed=config.seed,
            )

    report = {
        "config": asdict(config),
        "checkpoint": {
            "trainer": checkpoint.get("trainer"),
            "step": checkpoint.get("step"),
            "metrics": checkpoint.get("metrics", {}),
        },
        "device": device,
        "matchups": matchups,
    }
    output = Path(config.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report
