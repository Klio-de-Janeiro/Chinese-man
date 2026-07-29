"""Fine-tune the imitation checkpoint through PPO self-play."""

from __future__ import annotations

import argparse
import json

from ..config import load_yaml
from ..training.ppo import PPOConfig, train_ppo


def main() -> None:
    """Run PPO from one YAML configuration."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="ml/configs/ppo.yaml",
    )
    arguments = parser.parse_args()
    payload = load_yaml(arguments.config)
    config = PPOConfig.from_dict(payload["ppo"])
    metrics = train_ppo(config)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
