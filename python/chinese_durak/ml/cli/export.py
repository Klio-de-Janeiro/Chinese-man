"""Export a trained policy to validated ONNX artifacts."""

from __future__ import annotations

import argparse
import json

from ..config import load_yaml
from ..export import ExportConfig, export_onnx


def main() -> None:
    """Run ONNX export from one YAML configuration."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="ml/configs/evaluation.yaml",
    )
    arguments = parser.parse_args()
    payload = load_yaml(arguments.config)
    config = ExportConfig(**payload["export"])
    metadata = export_onnx(config)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
