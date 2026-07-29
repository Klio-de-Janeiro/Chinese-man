"""Behavior-cloning pretraining with an auxiliary value target."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from ..models import ModelConfig, PolicyValueNetwork
from .checkpoints import checkpoint_payload, save_checkpoint
from .data import ParquetDecisionDataset, collate_decisions


@dataclass(frozen=True)
class ImitationConfig:
    """Configure behavior cloning and validation."""

    dataset_dir: str
    output_dir: str
    seed: int = 2026
    epochs: int = 10
    steps_per_epoch: int = 2_000
    validation_steps: int = 200
    batch_size: int = 256
    num_workers: int = 4
    learning_rate: float = 3.0e-4
    weight_decay: float = 1.0e-4
    value_coefficient: float = 0.5
    max_grad_norm: float = 1.0
    amp: bool = True
    model: ModelConfig = field(default_factory=ModelConfig)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ImitationConfig:
        """Build nested configuration from YAML values."""

        payload = dict(value)
        payload["model"] = ModelConfig(**payload.get("model", {}))
        return cls(**payload)


def _seed_everything(seed: int) -> None:
    """Seed Python, NumPy, and all available torch devices."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _move_batch(
    batch: dict[str, Any],
    device: str,
) -> tuple[dict[str, torch.Tensor], torch.Tensor, torch.Tensor]:
    """Move one collated decision batch to the training device."""

    inputs = {
        name: value.to(device, non_blocking=True)
        for name, value in batch["inputs"].items()
    }
    targets = batch["targets"].to(device, non_blocking=True)
    outcomes = batch["outcomes"].to(device, non_blocking=True)
    return inputs, targets, outcomes


def _validate(
    model: PolicyValueNetwork,
    loader: DataLoader,
    device: str,
    steps: int,
    value_coefficient: float,
) -> dict[str, float]:
    """Evaluate a bounded number of validation batches."""

    model.eval()
    policy_total = 0.0
    value_total = 0.0
    correct = 0
    examples = 0
    batch_count = 0
    with torch.inference_mode():
        for batch in loader:
            if batch_count >= steps:
                break
            inputs, targets, outcomes = _move_batch(batch, device)
            logits, values = model(**inputs)
            policy_loss = nn.functional.cross_entropy(logits, targets)
            value_loss = nn.functional.mse_loss(values, outcomes)
            policy_total += float(policy_loss.item())
            value_total += float(value_loss.item())
            correct += int((logits.argmax(dim=1) == targets).sum())
            examples += int(targets.shape[0])
            batch_count += 1

    if batch_count == 0:
        raise RuntimeError("Validation split produced no decisions")
    policy = policy_total / batch_count
    value = value_total / batch_count
    return {
        "validation_policy_loss": policy,
        "validation_value_loss": value,
        "validation_loss": policy + value_coefficient * value,
        "validation_accuracy": correct / max(1, examples),
    }


def train_imitation(
    config: ImitationConfig,
) -> dict[str, float]:
    """Train a policy-value network and save the best checkpoint."""

    _seed_everything(config.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        torch.set_float32_matmul_precision("high")

    train_data = ParquetDecisionDataset(
        config.dataset_dir,
        split="train",
        seed=config.seed,
    )
    validation_data = ParquetDecisionDataset(
        config.dataset_dir,
        split="validation",
        seed=config.seed,
    )
    loader_options = {
        "batch_size": config.batch_size,
        "num_workers": config.num_workers,
        "collate_fn": collate_decisions,
        "pin_memory": device == "cuda",
        "persistent_workers": config.num_workers > 0,
    }
    train_loader = DataLoader(train_data, **loader_options)
    validation_loader = DataLoader(
        validation_data,
        **loader_options,
    )
    model = PolicyValueNetwork(config.model).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    use_amp = config.amp and device == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    output = Path(config.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics_path = output / "metrics.jsonl"
    best_loss = float("inf")
    global_step = 0
    final_metrics: dict[str, float] = {}

    for epoch in range(config.epochs):
        model.train()
        started = perf_counter()
        policy_total = 0.0
        value_total = 0.0
        train_steps = 0
        for batch in train_loader:
            if train_steps >= config.steps_per_epoch:
                break
            inputs, targets, outcomes = _move_batch(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(
                device_type=device,
                dtype=torch.float16,
                enabled=use_amp,
            ):
                logits, values = model(**inputs)
                policy_loss = nn.functional.cross_entropy(
                    logits,
                    targets,
                )
                value_loss = nn.functional.mse_loss(values, outcomes)
                loss = (
                    policy_loss
                    + config.value_coefficient * value_loss
                )

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(
                model.parameters(),
                config.max_grad_norm,
            )
            scaler.step(optimizer)
            scaler.update()
            policy_total += float(policy_loss.item())
            value_total += float(value_loss.item())
            global_step += 1
            train_steps += 1

        if train_steps == 0:
            raise RuntimeError("Training split produced no decisions")
        metrics = {
            "epoch": float(epoch + 1),
            "global_step": float(global_step),
            "train_policy_loss": policy_total / train_steps,
            "train_value_loss": value_total / train_steps,
            "epoch_seconds": perf_counter() - started,
        }
        metrics.update(
            _validate(
                model,
                validation_loader,
                device,
                config.validation_steps,
                config.value_coefficient,
            )
        )
        final_metrics = metrics
        with metrics_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(metrics, ensure_ascii=False) + "\n"
            )

        payload = checkpoint_payload(
            model=model,
            step=global_step,
            metrics=metrics,
            optimizer_state=optimizer.state_dict(),
            trainer="imitation",
        )
        save_checkpoint(output / "last.pt", payload)
        if metrics["validation_loss"] < best_loss:
            best_loss = metrics["validation_loss"]
            save_checkpoint(output / "best.pt", payload)

    (output / "training_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return final_metrics
