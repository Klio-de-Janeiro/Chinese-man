"""Episode simulation shared by dataset generation and evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from random import Random

from .agents import Agent
from .contracts import DecisionSample
from .environment import ChineseDurakEnv


@dataclass(frozen=True)
class EpisodeTrace:
    """Contain all decisions and final rewards from one game."""

    seed: int
    player_count: int
    decisions: tuple[DecisionSample, ...]
    rewards: tuple[float, ...]
    decision_count: int


def play_episode(
    agents: Sequence[Agent],
    seed: int,
    player_count: int,
    collect_decisions: bool = True,
) -> EpisodeTrace:
    """Play one deterministic legal episode."""

    if len(agents) != player_count:
        raise ValueError("One agent is required for every player")

    environment = ChineseDurakEnv()
    observation = environment.reset(
        seed=seed,
        player_count=player_count,
    )
    random = Random(seed)
    decisions: list[DecisionSample] = []
    episode_id = f"{player_count}-{seed}"

    while True:
        agent = agents[observation.viewer]
        action_index = agent.choose_action(observation, random)
        if (
            action_index < 0
            or action_index >= len(observation.legal_actions)
        ):
            raise RuntimeError(
                f"{agent.name} returned an illegal action index"
            )

        if collect_decisions:
            decisions.append(
                DecisionSample(
                    seed=seed,
                    player_count=player_count,
                    episode_id=episode_id,
                    observation=observation,
                    chosen_action_index=action_index,
                    teacher=agent.name,
                )
            )

        step = environment.step(action_index)
        if step.terminated:
            if step.rewards is None:
                raise RuntimeError("Terminal step has no rewards")
            rewards = step.rewards
            break
        if step.observation is None:
            raise RuntimeError("Active step has no observation")
        observation = step.observation

    completed = tuple(
        replace(
            decision,
            outcome=rewards[decision.observation.viewer],
        )
        for decision in decisions
    )
    return EpisodeTrace(
        seed=seed,
        player_count=player_count,
        decisions=completed,
        rewards=rewards,
        decision_count=int(environment.state["decision_count"]),
    )
