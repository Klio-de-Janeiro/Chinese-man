"""Benchmark direct C++ engine self-play."""

from __future__ import annotations

import argparse
import json

from ..benchmark import BenchmarkConfig, benchmark


def main() -> None:
    """Run the direct-engine benchmark."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument(
        "--players",
        type=int,
        choices=(2, 3),
        default=2,
    )
    parser.add_argument(
        "--agent",
        choices=("random", "heuristic"),
        default="random",
    )
    parser.add_argument("--start-seed", type=int, default=1)
    arguments = parser.parse_args()
    result = benchmark(
        BenchmarkConfig(
            games=arguments.games,
            player_count=arguments.players,
            agent=arguments.agent,
            start_seed=arguments.start_seed,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
