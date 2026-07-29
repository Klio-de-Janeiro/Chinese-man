"""Small YAML configuration loader with explicit error messages."""

from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load one mapping from a UTF-8 YAML file."""

    import yaml

    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Configuration root must be a mapping")
    return value
