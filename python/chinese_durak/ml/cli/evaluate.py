"""Evaluate one policy checkpoint against reference agents."""

from __future__ import annotations

import argparse
import json

from ..config import load_yaml
from ..evaluation import EvaluationConfig, evaluate_checkpoint


def main() -> None:
    """Run evaluation from one YAML configuration."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="ml/configs/evaluation.yaml",
    )
    arguments = parser.parse_args()
    payload = load_yaml(arguments.config)
    config = EvaluationConfig.from_dict(payload["evaluation"])
    report = evaluate_checkpoint(config)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
