"""Generate a teacher-play Parquet dataset."""

from __future__ import annotations

import argparse
import json

from ..config import load_yaml
from ..data_generation import GenerationConfig, generate_dataset


def main() -> None:
    """Run dataset generation from one YAML configuration."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="ml/configs/dataset.yaml",
    )
    arguments = parser.parse_args()
    payload = load_yaml(arguments.config)
    values = dict(payload["generation"])
    values["player_counts"] = tuple(
        values.get("player_counts", (2, 3))
    )
    config = GenerationConfig(**values)
    manifest = generate_dataset(config)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
