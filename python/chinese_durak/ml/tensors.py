"""Conversions between NumPy batches and torch model inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .batching import NumpyBatch

if TYPE_CHECKING:
    from torch import Tensor


def to_torch_inputs(
    batch: NumpyBatch,
    device: str | None = None,
) -> dict[str, Tensor]:
    """Convert one NumPy batch without copying when possible."""

    import torch

    inputs = {
        name: torch.from_numpy(value)
        for name, value in batch.to_dict().items()
    }
    if device is not None:
        inputs = {
            name: value.to(device, non_blocking=True)
            for name, value in inputs.items()
        }
    return inputs
