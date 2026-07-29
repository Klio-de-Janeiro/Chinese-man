"""Measure direct-engine simulation throughput."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from .agents import HeuristicAgent, RandomAgent
from .simulation import play_episode


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configure a reproducible single-process engine benchmark."""

    games: int = 1_000
    player_count: int = 2
    agent: str = "random"
    start_seed: int = 1


def benchmark(config: BenchmarkConfig) -> dict[str, float | str]:
    """Return games and decisions per second."""

    if config.games <= 0:
        raise ValueError("games must be positive")
    if config.player_count not in (2, 3):
        raise ValueError("player_count must be 2 or 3")
    if config.agent == "random":
        agent_type = RandomAgent
    elif config.agent == "heuristic":
        agent_type = HeuristicAgent
    else:
        raise ValueError("agent must be random or heuristic")

    agents = [agent_type() for _ in range(config.player_count)]
    decisions = 0
    started = perf_counter()
    for offset in range(config.games):
        trace = play_episode(
            agents=agents,
            seed=config.start_seed + offset,
            player_count=config.player_count,
            collect_decisions=False,
        )
        decisions += trace.decision_count

    elapsed = perf_counter() - started
    return {
        "agent": config.agent,
        "player_count": float(config.player_count),
        "games": float(config.games),
        "decisions": float(decisions),
        "seconds": elapsed,
        "games_per_second": config.games / elapsed,
        "decisions_per_second": decisions / elapsed,
    }
