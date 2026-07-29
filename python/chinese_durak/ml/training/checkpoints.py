"""Versioned PyTorch checkpoint utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chinese_durak import RULES_VERSION

from ..constants import ENCODER_VERSION, ML_SCHEMA_VERSION
from ..models import ModelConfig, PolicyValueNetwork


def checkpoint_payload(
    model: PolicyValueNetwork,
    step: int,
    metrics: dict[str, float],
    optimizer_state: dict[str, Any] | None = None,
    trainer: str = "unknown",
) -> dict[str, Any]:
    """Build a self-describing checkpoint dictionary."""

    return {
        "schema_version": ML_SCHEMA_VERSION,
        "encoder_version": ENCODER_VERSION,
        "rules_version": str(RULES_VERSION),
        "trainer": trainer,
        "step": step,
        "model_config": model.config.to_dict(),
        "model_state": model.state_dict(),
        "optimizer_state": optimizer_state,
        "metrics": metrics,
    }


def save_checkpoint(
    path: str | Path,
    payload: dict[str, Any],
) -> None:
    """Atomically replace one checkpoint file."""

    import torch

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(target)


def load_checkpoint(
    path: str | Path,
    device: str,
) -> tuple[PolicyValueNetwork, dict[str, Any]]:
    """Load and validate one compatible model checkpoint."""

    import torch

    payload = torch.load(
        path,
        map_location=device,
        weights_only=False,
    )
    if payload.get("schema_version") != ML_SCHEMA_VERSION:
        raise ValueError("Checkpoint ML schema is incompatible")
    if payload.get("encoder_version") != ENCODER_VERSION:
        raise ValueError("Checkpoint encoder is incompatible")
    if payload.get("rules_version") != str(RULES_VERSION):
        raise ValueError("Checkpoint rules version is incompatible")

    config = ModelConfig(**payload["model_config"])
    model = PolicyValueNetwork(config)
    model.load_state_dict(payload["model_state"])
    model.to(device)
    return model, payload
