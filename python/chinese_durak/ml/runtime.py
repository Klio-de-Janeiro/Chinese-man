"""ONNX inference with a deterministic heuristic fallback."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random
from typing import Any

from chinese_durak import RULES_VERSION

from .agents import HeuristicAgent
from .batching import encode_batch
from .constants import ENCODER_VERSION, ML_SCHEMA_VERSION
from .contracts import PlayerObservation


class FallbackBotRuntime:
    """Use a compatible ONNX policy or fall back without breaking games."""

    def __init__(
        self,
        model_path: str | Path,
        metadata_path: str | Path,
    ) -> None:
        """Load optional release artifacts and preserve the failure reason."""

        self._model_path = Path(model_path)
        self._metadata_path = Path(metadata_path)
        self._session: Any = None
        self._metadata: dict[str, Any] = {}
        self._reason: str | None = None
        self._fallback = HeuristicAgent()
        self._load()

    @property
    def status(self) -> dict[str, Any]:
        """Return public diagnostics without filesystem details."""

        return {
            "backend": (
                "onnx" if self._session is not None else "heuristic"
            ),
            "modelVersion": self._metadata.get("model_version"),
            "reason": self._reason,
        }

    def choose_action(
        self,
        observation: PlayerObservation,
        random: Random,
    ) -> int:
        """Choose a legal action and disable ONNX after any runtime error."""

        if self._session is None:
            return self._fallback.choose_action(observation, random)

        try:
            batch = encode_batch([observation])
            logits = self._session.run(
                ["policy_logits"],
                batch.to_dict(),
            )[0][0, : len(observation.legal_actions)]
            return int(logits.argmax())
        except Exception as error:
            self._session = None
            self._reason = f"inference failed: {type(error).__name__}"
            return self._fallback.choose_action(observation, random)

    def _load(self) -> None:
        """Load compatible metadata before importing ONNX Runtime."""

        if not self._model_path.is_file():
            self._reason = "model file is not installed"
            return
        if not self._metadata_path.is_file():
            self._reason = "metadata file is not installed"
            return

        try:
            self._metadata = json.loads(
                self._metadata_path.read_text(encoding="utf-8")
            )
            expected = {
                "schema_version": ML_SCHEMA_VERSION,
                "encoder_version": ENCODER_VERSION,
                "rules_version": str(RULES_VERSION),
            }
            for field, value in expected.items():
                if self._metadata.get(field) != value:
                    raise ValueError(f"incompatible {field}")

            import onnxruntime as ort

            self._session = ort.InferenceSession(
                str(self._model_path),
                providers=["CPUExecutionProvider"],
            )
            self._reason = None
        except Exception as error:
            self._session = None
            self._reason = f"load failed: {type(error).__name__}"
