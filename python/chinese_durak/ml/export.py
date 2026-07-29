"""Validated ONNX export for the production bot runtime."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from chinese_durak import RULES_VERSION

from .batching import encode_batch
from .constants import ENCODER_VERSION, ML_SCHEMA_VERSION
from .environment import ChineseDurakEnv
from .tensors import to_torch_inputs

MODEL_INPUT_NAMES = (
    "hand_cards",
    "table_cards",
    "table_zones",
    "history",
    "history_lengths",
    "global_features",
    "actions",
    "action_mask",
    "trump_suit",
)
MODEL_OUTPUT_NAMES = ("policy_logits", "value")


@dataclass(frozen=True)
class ExportConfig:
    """Configure ONNX export and numerical validation."""

    checkpoint: str
    model_path: str
    metadata_path: str
    model_version: str = "bot_v1"
    opset: int = 18
    tolerance: float = 1.0e-4
    evaluation_report: str | None = None
    minimum_heuristic_win_rate: float = 0.6


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for one file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_promotion(
    config: ExportConfig,
) -> dict[str, Any] | None:
    """Require the configured two-player heuristic quality gate."""

    if not 0.0 <= config.minimum_heuristic_win_rate <= 1.0:
        raise ValueError("minimum_heuristic_win_rate must be in [0, 1]")
    if config.evaluation_report is None:
        return None
    report_path = Path(config.evaluation_report)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    matchup = report["matchups"]["2p_vs_heuristic"]
    win_rate = float(matchup["first_place_rate"])
    if win_rate < config.minimum_heuristic_win_rate:
        raise RuntimeError(
            "Checkpoint did not pass the heuristic promotion gate: "
            f"{win_rate:.4f} < {config.minimum_heuristic_win_rate:.4f}"
        )
    return {
        "report_sha256": _sha256(report_path),
        "heuristic_win_rate": win_rate,
        "minimum_heuristic_win_rate": (
            config.minimum_heuristic_win_rate
        ),
    }


def export_onnx(config: ExportConfig) -> dict[str, Any]:
    """Export a checkpoint and reject numerically different output."""

    import onnxruntime as ort
    import torch

    from .training.checkpoints import load_checkpoint

    checkpoint_path = Path(config.checkpoint)
    model_path = Path(config.model_path)
    metadata_path = Path(config.metadata_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    promotion = _validate_promotion(config)
    model, checkpoint = load_checkpoint(checkpoint_path, "cpu")
    model.eval()
    observation = ChineseDurakEnv().reset(seed=7, player_count=3)
    numpy_batch = encode_batch([observation])
    inputs = to_torch_inputs(numpy_batch)
    input_values = tuple(inputs[name] for name in MODEL_INPUT_NAMES)

    with torch.inference_mode():
        expected_logits, expected_value = model(*input_values)
    dynamic_axes = {
        name: {0: "batch"}
        for name in MODEL_INPUT_NAMES
    }
    dynamic_axes["actions"][1] = "legal_actions"
    dynamic_axes["action_mask"][1] = "legal_actions"
    dynamic_axes["policy_logits"] = {
        0: "batch",
        1: "legal_actions",
    }
    dynamic_axes["value"] = {0: "batch"}
    torch.onnx.export(
        model,
        input_values,
        model_path,
        input_names=list(MODEL_INPUT_NAMES),
        output_names=list(MODEL_OUTPUT_NAMES),
        dynamic_axes=dynamic_axes,
        opset_version=config.opset,
        dynamo=False,
    )

    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    actual_logits, actual_value = session.run(
        list(MODEL_OUTPUT_NAMES),
        numpy_batch.to_dict(),
    )
    logits_error = float(
        np.max(
            np.abs(
                actual_logits
                - expected_logits.detach().cpu().numpy()
            )
        )
    )
    value_error = float(
        np.max(
            np.abs(
                actual_value
                - expected_value.detach().cpu().numpy()
            )
        )
    )
    maximum_error = max(logits_error, value_error)
    if maximum_error > config.tolerance:
        model_path.unlink(missing_ok=True)
        raise RuntimeError(
            "ONNX validation exceeded tolerance: "
            f"{maximum_error:.8f} > {config.tolerance:.8f}"
        )

    metadata = {
        "model_version": config.model_version,
        "schema_version": ML_SCHEMA_VERSION,
        "encoder_version": ENCODER_VERSION,
        "rules_version": str(RULES_VERSION),
        "created_at": datetime.now(UTC).isoformat(),
        "model_config": checkpoint["model_config"],
        "trainer": checkpoint.get("trainer"),
        "training_step": checkpoint.get("step"),
        "training_metrics": checkpoint.get("metrics", {}),
        "input_names": list(MODEL_INPUT_NAMES),
        "output_names": list(MODEL_OUTPUT_NAMES),
        "checkpoint_sha256": _sha256(checkpoint_path),
        "onnx_sha256": _sha256(model_path),
        "opset": config.opset,
        "maximum_validation_error": maximum_error,
        "promotion": promotion,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata
