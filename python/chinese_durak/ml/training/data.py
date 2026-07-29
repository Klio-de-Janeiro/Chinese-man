"""Streaming Parquet loaders and dynamic-action collation."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from pathlib import Path
from random import Random
from typing import Any, Literal

import numpy as np
import torch
from torch.utils.data import IterableDataset, get_worker_info

from ..batching import encode_batch
from ..contracts import PlayerObservation
from ..tensors import to_torch_inputs


class ParquetDecisionDataset(IterableDataset[dict[str, Any]]):
    """Stream shards with a deterministic seed-based train split."""

    def __init__(
        self,
        dataset_dir: str | Path,
        split: Literal["train", "validation"],
        seed: int,
        shuffle_buffer: int = 16_384,
        validation_modulus: int = 10,
    ) -> None:
        """Index Parquet shards without loading their rows."""

        super().__init__()
        self.files = sorted(Path(dataset_dir).glob("part-*.parquet"))
        if not self.files:
            raise FileNotFoundError(
                f"No Parquet shards found in {dataset_dir}"
            )
        self.split = split
        self.seed = seed
        self.shuffle_buffer = (
            shuffle_buffer if split == "train" else 0
        )
        self.validation_modulus = validation_modulus

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Yield decoded rows assigned to the current DataLoader worker."""

        import pyarrow.parquet as pq

        worker = get_worker_info()
        if worker is None:
            files = self.files
            worker_id = 0
        else:
            files = self.files[worker.id :: worker.num_workers]
            worker_id = worker.id

        random = Random(self.seed + worker_id)
        buffer: list[dict[str, Any]] = []
        for path in files:
            parquet = pq.ParquetFile(path)
            for batch in parquet.iter_batches(
                batch_size=4096,
                columns=(
                    "seed",
                    "observation_json",
                    "chosen_action_index",
                    "outcome",
                ),
            ):
                for row in batch.to_pylist():
                    if not self._belongs_to_split(int(row["seed"])):
                        continue
                    decoded = {
                        "observation": PlayerObservation.from_dict(
                            json.loads(row["observation_json"])
                        ),
                        "chosen_action_index": int(
                            row["chosen_action_index"]
                        ),
                        "outcome": float(row["outcome"]),
                    }
                    if self.shuffle_buffer <= 0:
                        yield decoded
                        continue
                    if len(buffer) < self.shuffle_buffer:
                        buffer.append(decoded)
                        continue

                    index = random.randrange(len(buffer))
                    yield buffer[index]
                    buffer[index] = decoded

        random.shuffle(buffer)
        yield from buffer

    def _belongs_to_split(self, seed: int) -> bool:
        """Keep every episode entirely in one deterministic split."""

        is_validation = seed % self.validation_modulus == 0
        return (
            is_validation
            if self.split == "validation"
            else not is_validation
        )


def collate_decisions(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Build padded tensors and supervised targets."""

    observations = [row["observation"] for row in rows]
    inputs = to_torch_inputs(encode_batch(observations))
    targets = torch.from_numpy(
        np.asarray(
            [row["chosen_action_index"] for row in rows],
            dtype=np.int64,
        )
    )
    outcomes = torch.from_numpy(
        np.asarray(
            [row["outcome"] for row in rows],
            dtype=np.float32,
        )
    )
    return {
        "inputs": inputs,
        "targets": targets,
        "outcomes": outcomes,
    }
