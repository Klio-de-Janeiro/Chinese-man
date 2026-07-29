# ML architecture

## Runtime boundary

```text
GameEngine state
    -> private PlayerObservation
    -> legal action encoder
    -> ONNX policy logits
    -> selected legal action
    -> GameEngine.apply()
```

The neural component cannot construct arbitrary commands. It returns an
index into the exact legal-action sequence supplied by the engine, and the
engine validates the selected native action again.

## Source layout

```text
python/chinese_durak/ml/
  contracts.py          Versioned observations and samples
  observation.py        Leak-free projection and feature encoder
  environment.py        Direct pybind11 self-play environment
  agents/               Random, greedy, heuristic, and policy agents
  dataset.py            Streaming Parquet writer
  data_generation.py    Process-parallel teacher games
  models/               Policy-value PyTorch network
  training/             Imitation learning and PPO
  evaluation.py         Paired-seed cross-play
  export.py             Validated ONNX export
  runtime.py            ONNX inference with heuristic fallback
```

## State encoding

Cards are compact integers from 0 to 51. The model embeds rank, suit, zone,
and whether the card is trump. Hand order is intentionally ignored through
masked set pooling. Table positions preserve attack/defense slot identity.

The history GRU receives the last 64 public actions. Actor indices and global
player features are rotated relative to the current viewer, reducing seat
bias while preserving the viewer's information set.

## Action encoding

Each action is represented by:

```text
(kind, optional card, optional target slot)
```

Action embeddings are scored against one shared state vector. Padding is
masked before the categorical policy distribution is constructed.

## Training lifecycle

1. Generate reproducible teacher games directly through pybind11.
2. Train policy and value heads with behavior cloning and final outcomes.
3. Initialize PPO from the best imitation checkpoint.
4. Mix current self-play, historical policies, and heuristic opponents.
5. Evaluate every seat with paired seeds.
6. Export only a version-compatible checkpoint.
7. Verify ONNX output against PyTorch before release.

## Operational safety

- Rules remain in C++ and are not duplicated in model code.
- Opponent hands and deck order never enter `PlayerObservation`.
- Dataset, checkpoint, and release metadata carry compatibility versions.
- Runtime exceptions disable ONNX for the process and fall back to a legal
  heuristic policy.
- API health and `/api/bot/status` expose the active backend.
