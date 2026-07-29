"""Streaming Parquet storage for imitation and replay decisions."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .contracts import DecisionSample


class ParquetDecisionWriter:
    """Write bounded row groups without retaining a full dataset in RAM."""

    def __init__(
        self,
        path: Path,
        row_group_size: int = 16_384,
    ) -> None:
        """Open a compressed Parquet shard."""

        import pyarrow as pa
        import pyarrow.parquet as pq

        path.parent.mkdir(parents=True, exist_ok=True)
        self._schema = pa.schema(
            [
                ("schema_version", pa.string()),
                ("rules_version", pa.string()),
                ("seed", pa.int64()),
                ("player_count", pa.int8()),
                ("episode_id", pa.string()),
                ("decision_index", pa.int32()),
                ("actor", pa.int8()),
                ("observation_json", pa.string()),
                ("chosen_action_index", pa.int16()),
                ("teacher", pa.string()),
                ("outcome", pa.float32()),
            ]
        )
        self._pa = pa
        self._writer = pq.ParquetWriter(
            path,
            self._schema,
            compression="zstd",
        )
        self._row_group_size = row_group_size
        self._buffer: list[dict[str, object]] = []
        self.rows_written = 0

    def append(self, sample: DecisionSample) -> None:
        """Buffer one decision and flush a complete row group."""

        value = sample.to_dict()
        self._buffer.append(
            {
                "schema_version": value["schema_version"],
                "rules_version": value["rules_version"],
                "seed": value["seed"],
                "player_count": value["player_count"],
                "episode_id": value["episode_id"],
                "decision_index": value["decision_index"],
                "actor": value["actor"],
                "observation_json": json.dumps(
                    value["observation"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "chosen_action_index": value[
                    "chosen_action_index"
                ],
                "teacher": value["teacher"],
                "outcome": value["outcome"],
            }
        )
        if len(self._buffer) >= self._row_group_size:
            self.flush()

    def extend(self, samples: Iterable[DecisionSample]) -> None:
        """Append multiple decisions."""

        for sample in samples:
            self.append(sample)

    def flush(self) -> None:
        """Write the current row group when it is non-empty."""

        if not self._buffer:
            return
        table = self._pa.Table.from_pylist(
            self._buffer,
            schema=self._schema,
        )
        self._writer.write_table(table)
        self.rows_written += len(self._buffer)
        self._buffer.clear()

    def close(self) -> None:
        """Flush and close the shard."""

        self.flush()
        self._writer.close()

    def __enter__(self) -> ParquetDecisionWriter:
        """Return the open writer."""

        return self

    def __exit__(self, *_errors: object) -> None:
        """Close the shard on normal or exceptional exit."""

        self.close()
