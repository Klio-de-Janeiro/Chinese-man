"""Tests for model promotion gates that do not require PyTorch."""

from __future__ import annotations

import json

import pytest
from chinese_durak.ml.export import ExportConfig, _validate_promotion


def test_export_rejects_checkpoint_below_quality_gate(tmp_path) -> None:
    """Prevent weak checkpoints from becoming release models."""

    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "matchups": {
                    "2p_vs_heuristic": {
                        "first_place_rate": 0.59,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    config = ExportConfig(
        checkpoint="unused.pt",
        model_path="unused.onnx",
        metadata_path="unused.json",
        evaluation_report=str(report),
        minimum_heuristic_win_rate=0.6,
    )

    with pytest.raises(RuntimeError, match="promotion gate"):
        _validate_promotion(config)


def test_export_accepts_checkpoint_at_quality_gate(tmp_path) -> None:
    """Record the verified heuristic win rate in release metadata."""

    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "matchups": {
                    "2p_vs_heuristic": {
                        "first_place_rate": 0.61,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    config = ExportConfig(
        checkpoint="unused.pt",
        model_path="unused.onnx",
        metadata_path="unused.json",
        evaluation_report=str(report),
        minimum_heuristic_win_rate=0.6,
    )

    result = _validate_promotion(config)

    assert result is not None
    assert result["heuristic_win_rate"] == 0.61
