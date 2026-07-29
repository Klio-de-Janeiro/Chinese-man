"""On-policy PPO self-play with heuristic and historical opponents."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import torch
from torch import nn

from ..agents import HeuristicAgent, TorchPolicyAgent
from ..batching import encode_batch
from ..contracts import PlayerObservation
from ..environment import ChineseDurakEnv
from ..models import PolicyValueNetwork
from ..tensors import to_torch_inputs
from .checkpoints import (
    checkpoint_payload,
    load_checkpoint,
    save_checkpoint,
)


@dataclass(frozen=True)
class PPOConfig:
    """Configure recurrent multi-agent PPO self-play."""

    base_checkpoint: str
    output_dir: str
    seed: int = 2026
    updates: int = 100
    episodes_per_update: int = 256
    player_counts: tuple[int, ...] = (2, 3)
    batch_size: int = 1024
    ppo_epochs: int = 4
    learning_rate: float = 3.0e-4
    weight_decay: float = 1.0e-4
    gamma: float = 1.0
    gae_lambda: float = 0.95
    clip_ratio: float = 0.2
    entropy_coefficient: float = 0.01
    value_coefficient: float = 0.5
    max_grad_norm: float = 0.5
    heuristic_probability: float = 0.2
    historical_probability: float = 0.3
    checkpoint_every: int = 5
    max_historical_models: int = 4

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PPOConfig:
        """Build configuration while normalizing sequence fields."""

        payload = dict(value)
        payload["player_counts"] = tuple(
            payload.get("player_counts", (2, 3))
        )
        return cls(**payload)

    def validate(self) -> None:
        """Reject settings that break on-policy assumptions."""

        if self.updates <= 0 or self.episodes_per_update <= 0:
            raise ValueError(
                "updates and episodes_per_update must be positive"
            )
        if not self.player_counts:
            raise ValueError("player_counts cannot be empty")
        if any(count not in (2, 3) for count in self.player_counts):
            raise ValueError("player_counts may contain only 2 and 3")

        opponent_probability = (
            self.heuristic_probability
            + self.historical_probability
        )
        if opponent_probability < 0 or opponent_probability > 1:
            raise ValueError("Opponent probabilities must be in [0, 1]")


@dataclass
class RolloutTransition:
    """Store one learner action and its PPO targets."""

    observation: PlayerObservation
    action_index: int
    old_log_probability: float
    old_value: float
    actor: int
    advantage: float = 0.0
    return_value: float = 0.0


def _policy_decision(
    model: PolicyValueNetwork,
    observation: PlayerObservation,
    device: str,
) -> tuple[int, float, float]:
    """Sample one on-policy decision and preserve its old statistics."""

    inputs = to_torch_inputs(
        encode_batch([observation]),
        device,
    )
    with torch.inference_mode():
        logits, values = model(**inputs)
        distribution = torch.distributions.Categorical(logits=logits[0])
        action = distribution.sample()
        log_probability = distribution.log_prob(action)
    return (
        int(action.item()),
        float(log_probability.item()),
        float(values[0].item()),
    )


def _finish_actor_trajectory(
    transitions: list[RolloutTransition],
    reward: float,
    gamma: float,
    gae_lambda: float,
) -> None:
    """Compute actor-specific GAE after an episode terminates."""

    gae = 0.0
    next_value = 0.0
    for index in range(len(transitions) - 1, -1, -1):
        transition = transitions[index]
        step_reward = reward if index == len(transitions) - 1 else 0.0
        delta = (
            step_reward
            + gamma * next_value
            - transition.old_value
        )
        gae = delta + gamma * gae_lambda * gae
        transition.advantage = gae
        transition.return_value = gae + transition.old_value
        next_value = transition.old_value


def _collect_episode(
    model: PolicyValueNetwork,
    historical_agents: list[TorchPolicyAgent],
    config: PPOConfig,
    device: str,
    seed: int,
) -> tuple[list[RolloutTransition], tuple[float, ...], int]:
    """Collect one self-play or league episode."""

    random_state = random.Random(seed)
    player_count = config.player_counts[
        seed % len(config.player_counts)
    ]
    environment = ChineseDurakEnv()
    observation = environment.reset(seed, player_count)
    mode_value = random_state.random()
    historical_cutoff = (
        config.heuristic_probability
        + config.historical_probability
    )
    if mode_value >= historical_cutoff:
        learner_seats = set(range(player_count))
        opponent_agents: dict[int, Any] = {}
    else:
        learner = random_state.randrange(player_count)
        learner_seats = {learner}
        if (
            mode_value >= config.heuristic_probability
            and historical_agents
        ):
            opponent_agents = {
                seat: random_state.choice(historical_agents)
                for seat in range(player_count)
                if seat != learner
            }
        else:
            opponent_agents = {
                seat: HeuristicAgent()
                for seat in range(player_count)
                if seat != learner
            }

    transitions: list[RolloutTransition] = []
    while True:
        actor = observation.viewer
        if actor in learner_seats:
            action_index, log_probability, value = _policy_decision(
                model,
                observation,
                device,
            )
            transitions.append(
                RolloutTransition(
                    observation=observation,
                    action_index=action_index,
                    old_log_probability=log_probability,
                    old_value=value,
                    actor=actor,
                )
            )
        else:
            action_index = opponent_agents[actor].choose_action(
                observation,
                random_state,
            )

        step = environment.step(action_index)
        if step.terminated:
            if step.rewards is None:
                raise RuntimeError("Terminal rollout has no rewards")
            rewards = step.rewards
            break
        if step.observation is None:
            raise RuntimeError("Active rollout has no observation")
        observation = step.observation

    for actor in learner_seats:
        actor_transitions = [
            transition
            for transition in transitions
            if transition.actor == actor
        ]
        if actor_transitions:
            _finish_actor_trajectory(
                actor_transitions,
                rewards[actor],
                config.gamma,
                config.gae_lambda,
            )

    return (
        transitions,
        rewards,
        int(environment.state["decision_count"]),
    )


def _load_historical_agents(
    output_dir: Path,
    device: str,
    limit: int,
) -> list[TorchPolicyAgent]:
    """Load the most recent compatible league policies."""

    paths = sorted(
        (output_dir / "league").glob("*.pt"),
        key=lambda path: path.stat().st_mtime,
    )[-limit:]
    agents = []
    for path in paths:
        model, _ = load_checkpoint(path, device)
        model.eval()
        agents.append(
            TorchPolicyAgent(
                model=model,
                device=device,
                deterministic=False,
            )
        )
    return agents


def _snapshot_historical_agent(
    model: PolicyValueNetwork,
    device: str,
) -> TorchPolicyAgent:
    """Freeze the current parameters as one historical opponent."""

    snapshot = PolicyValueNetwork(model.config)
    snapshot.load_state_dict(model.state_dict())
    snapshot.to(device)
    snapshot.eval()
    return TorchPolicyAgent(
        model=snapshot,
        device=device,
        deterministic=False,
    )


def _ppo_update(
    model: PolicyValueNetwork,
    optimizer: torch.optim.Optimizer,
    transitions: list[RolloutTransition],
    config: PPOConfig,
    device: str,
) -> dict[str, float]:
    """Run clipped PPO optimization over one rollout."""

    advantages = np.asarray(
        [transition.advantage for transition in transitions],
        dtype=np.float32,
    )
    advantages = (
        advantages - advantages.mean()
    ) / (advantages.std() + 1.0e-8)
    indices = np.arange(len(transitions))
    metrics = {
        "policy_loss": 0.0,
        "value_loss": 0.0,
        "entropy": 0.0,
        "approx_kl": 0.0,
        "clip_fraction": 0.0,
    }
    batch_count = 0
    model.train()
    for _ in range(config.ppo_epochs):
        np.random.shuffle(indices)
        for start in range(0, len(indices), config.batch_size):
            batch_indices = indices[start : start + config.batch_size]
            batch_transitions = [
                transitions[index] for index in batch_indices
            ]
            inputs = to_torch_inputs(
                encode_batch(
                    [
                        transition.observation
                        for transition in batch_transitions
                    ]
                ),
                device,
            )
            actions = torch.tensor(
                [
                    transition.action_index
                    for transition in batch_transitions
                ],
                dtype=torch.long,
                device=device,
            )
            old_log_probabilities = torch.tensor(
                [
                    transition.old_log_probability
                    for transition in batch_transitions
                ],
                dtype=torch.float32,
                device=device,
            )
            old_values = torch.tensor(
                [
                    transition.old_value
                    for transition in batch_transitions
                ],
                dtype=torch.float32,
                device=device,
            )
            returns = torch.tensor(
                [
                    transition.return_value
                    for transition in batch_transitions
                ],
                dtype=torch.float32,
                device=device,
            )
            batch_advantages = torch.from_numpy(
                advantages[batch_indices]
            ).to(device)
            logits, values = model(**inputs)
            distribution = torch.distributions.Categorical(logits=logits)
            log_probabilities = distribution.log_prob(actions)
            entropy = distribution.entropy().mean()
            log_ratio = log_probabilities - old_log_probabilities
            ratio = log_ratio.exp()
            unclipped = ratio * batch_advantages
            clipped = (
                ratio.clamp(
                    1.0 - config.clip_ratio,
                    1.0 + config.clip_ratio,
                )
                * batch_advantages
            )
            policy_loss = -torch.minimum(unclipped, clipped).mean()
            clipped_values = old_values + (
                values - old_values
            ).clamp(-config.clip_ratio, config.clip_ratio)
            value_loss = 0.5 * torch.maximum(
                (values - returns).square(),
                (clipped_values - returns).square(),
            ).mean()
            loss = (
                policy_loss
                + config.value_coefficient * value_loss
                - config.entropy_coefficient * entropy
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(
                model.parameters(),
                config.max_grad_norm,
            )
            optimizer.step()
            with torch.no_grad():
                approx_kl = (
                    (ratio - 1.0) - log_ratio
                ).mean()
                clip_fraction = (
                    (ratio - 1.0).abs() > config.clip_ratio
                ).float().mean()

            metrics["policy_loss"] += float(policy_loss.item())
            metrics["value_loss"] += float(value_loss.item())
            metrics["entropy"] += float(entropy.item())
            metrics["approx_kl"] += float(approx_kl.item())
            metrics["clip_fraction"] += float(clip_fraction.item())
            batch_count += 1

    return {
        name: value / max(1, batch_count)
        for name, value in metrics.items()
    }


def train_ppo(config: PPOConfig) -> dict[str, float]:
    """Fine-tune an imitation checkpoint through PPO self-play."""

    config.validate()
    random.seed(config.seed)
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _ = load_checkpoint(config.base_checkpoint, device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    output = Path(config.output_dir)
    league_dir = output / "league"
    output.mkdir(parents=True, exist_ok=True)
    league_dir.mkdir(parents=True, exist_ok=True)
    historical_agents = _load_historical_agents(
        output,
        device,
        config.max_historical_models,
    )
    metrics_path = output / "metrics.jsonl"
    final_metrics: dict[str, float] = {}
    for update in range(1, config.updates + 1):
        started = perf_counter()
        model.eval()
        transitions: list[RolloutTransition] = []
        rewards: list[float] = []
        decision_counts = []
        for episode in range(config.episodes_per_update):
            seed = (
                config.seed
                + (update - 1) * config.episodes_per_update
                + episode
            )
            episode_transitions, episode_rewards, decisions = (
                _collect_episode(
                    model,
                    historical_agents,
                    config,
                    device,
                    seed,
                )
            )
            transitions.extend(episode_transitions)
            rewards.extend(episode_rewards)
            decision_counts.append(decisions)

        if not transitions:
            raise RuntimeError("PPO rollout produced no learner decisions")
        metrics = _ppo_update(
            model,
            optimizer,
            transitions,
            config,
            device,
        )
        metrics.update(
            {
                "update": float(update),
                "transitions": float(len(transitions)),
                "mean_reward": float(np.mean(rewards)),
                "mean_decisions": float(np.mean(decision_counts)),
                "rollout_and_update_seconds": (
                    perf_counter() - started
                ),
            }
        )
        final_metrics = metrics
        with metrics_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(metrics, ensure_ascii=False) + "\n"
            )

        payload = checkpoint_payload(
            model=model,
            step=update,
            metrics=metrics,
            optimizer_state=optimizer.state_dict(),
            trainer="ppo",
        )
        save_checkpoint(output / "last.pt", payload)
        if update % config.checkpoint_every == 0:
            save_checkpoint(
                league_dir / f"update-{update:05d}.pt",
                payload,
            )
            historical_agents.append(
                _snapshot_historical_agent(model, device)
            )
            historical_agents = historical_agents[
                -config.max_historical_models :
            ]

    (output / "training_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return final_metrics
