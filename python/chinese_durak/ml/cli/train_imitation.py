"""Train the initial policy-value checkpoint."""

from __future__ import annotations

import argparse
import json

from ..config import load_yaml
from ..training.imitation import ImitationConfig, train_imitation


def main() -> None:
    """Run behavior cloning from one YAML configuration."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="ml/configs/imitation.yaml",
    )
    arguments = parser.parse_args()
    payload = load_yaml(arguments.config)
    config = ImitationConfig.from_dict(payload["imitation"])
    metrics = train_imitation(config)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
