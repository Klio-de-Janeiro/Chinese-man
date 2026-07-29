"""Parallel teacher-play dataset generation."""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random
from time import perf_counter

from chinese_durak import RULES_VERSION

from .agents import Agent, GreedyAgent, HeuristicAgent, RandomAgent
from .constants import ENCODER_VERSION, ML_SCHEMA_VERSION
from .dataset import ParquetDecisionWriter
from .simulation import play_episode


@dataclass(frozen=True)
class GenerationConfig:
    """Configure deterministic imitation dataset generation."""

    output_dir: str
    games: int = 10_000
    workers: int = 4
    start_seed: int = 1
    player_counts: tuple[int, ...] = (2, 3)
    row_group_size: int = 16_384
    heuristic_probability: float = 0.8
    greedy_probability: float = 0.15
    random_probability: float = 0.05

    def validate(self) -> None:
        """Reject invalid and non-reproducible settings."""

        if self.games <= 0:
            raise ValueError("games must be positive")
        if self.workers <= 0:
            raise ValueError("workers must be positive")
        if not self.player_counts:
            raise ValueError("player_counts cannot be empty")
        if any(count not in (2, 3) for count in self.player_counts):
            raise ValueError("player_counts may contain only 2 and 3")

        probability = (
            self.heuristic_probability
            + self.greedy_probability
            + self.random_probability
        )
        if abs(probability - 1.0) > 1.0e-6:
            raise ValueError("teacher probabilities must sum to one")


@dataclass(frozen=True)
class ShardResult:
    """Report one completed worker shard."""

    path: str
    games: int
    decisions: int
    elapsed_seconds: float


def _sample_agent(
    random: Random,
    config: GenerationConfig,
) -> Agent:
    """Sample one teacher according to the configured mixture."""

    value = random.random()
    if value < config.heuristic_probability:
        return HeuristicAgent()
    if value < (
        config.heuristic_probability
        + config.greedy_probability
    ):
        return GreedyAgent()
    return RandomAgent()


def _generate_shard(
    config: GenerationConfig,
    shard_index: int,
    seed_start: int,
    game_count: int,
) -> ShardResult:
    """Generate one deterministic shard inside a worker process."""

    output = Path(config.output_dir)
    path = output / f"part-{shard_index:05d}.parquet"
    started = perf_counter()
    decisions = 0
    with ParquetDecisionWriter(
        path,
        row_group_size=config.row_group_size,
    ) as writer:
        for offset in range(game_count):
            seed = seed_start + offset
            random = Random(seed)
            player_count = config.player_counts[
                seed % len(config.player_counts)
            ]
            agents = [
                _sample_agent(random, config)
                for _ in range(player_count)
            ]
            trace = play_episode(
                agents=agents,
                seed=seed,
                player_count=player_count,
            )
            writer.extend(trace.decisions)
            decisions += len(trace.decisions)

    return ShardResult(
        path=str(path),
        games=game_count,
        decisions=decisions,
        elapsed_seconds=perf_counter() - started,
    )


def generate_dataset(
    config: GenerationConfig,
) -> dict[str, object]:
    """Generate independent Parquet shards and one manifest."""

    config.validate()
    output = Path(config.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    worker_count = min(config.workers, config.games)
    base_games, remainder = divmod(config.games, worker_count)
    jobs = []
    seed = config.start_seed
    for index in range(worker_count):
        count = base_games + int(index < remainder)
        jobs.append((index, seed, count))
        seed += count

    if worker_count == 1:
        results = [
            _generate_shard(config, *jobs[0])
        ]
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(_generate_shard, config, *job)
                for job in jobs
            ]
            results = [future.result() for future in futures]

    manifest = {
        "schema_version": ML_SCHEMA_VERSION,
        "encoder_version": ENCODER_VERSION,
        "rules_version": str(RULES_VERSION),
        "config": asdict(config),
        "games": sum(result.games for result in results),
        "decisions": sum(result.decisions for result in results),
        "elapsed_seconds": max(
            result.elapsed_seconds for result in results
        ),
        "shards": [asdict(result) for result in results],
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
