# Neural agent pipeline

This directory contains the complete second-option pipeline:

```text
heuristic teacher games
    -> Parquet decisions
    -> behavior cloning
    -> PPO self-play league
    -> paired-seed evaluation
    -> validated ONNX release
    -> FastAPI inference
```

The C++ `GameEngine` remains the only authority for rules and state changes.
The network receives a private `PlayerObservation` and scores only actions
already returned by `GameEngine.legal_actions()`.

## Privacy contract

The observation contains:

- the acting player's hand;
- table cards and trump;
- deck and discard sizes;
- opponent card counts, activity, and placements;
- public flags and the last 64 public actions;
- the current legal action list.

It never contains opponent hands or the deck order. The schema and feature
encoder have independent version identifiers so incompatible datasets and
models fail closed.

## Installation

From PowerShell in the project root:

```powershell
.\scripts\ml-bootstrap.ps1
```

The full pipeline benefits from an NVIDIA GPU. Dataset generation and the
game simulator are CPU workloads; imitation learning and PPO updates are
PyTorch workloads.

## Fast validation

The smoke pipeline uses small datasets and tiny training schedules:

```powershell
.\scripts\ml-smoke.ps1
```

It exercises the simulator, Parquet writer, imitation trainer, PPO league,
evaluation, ONNX export, and ONNX Runtime validation. Smoke weights are kept
under `artifacts/ml-smoke` and are not release models.

## Full training

Review the YAML files in `ml/configs`, then run:

```powershell
.\scripts\ml-train.ps1
```

The stages can also be run separately:

```powershell
.\.venv\Scripts\python.exe -m chinese_durak.ml.cli.generate_dataset `
  --config ml/configs/dataset.yaml

.\.venv\Scripts\python.exe -m chinese_durak.ml.cli.train_imitation `
  --config ml/configs/imitation.yaml

.\.venv\Scripts\python.exe -m chinese_durak.ml.cli.train_ppo `
  --config ml/configs/ppo.yaml

.\.venv\Scripts\python.exe -m chinese_durak.ml.cli.evaluate `
  --config ml/configs/evaluation.yaml

.\.venv\Scripts\python.exe -m chinese_durak.ml.cli.export `
  --config ml/configs/evaluation.yaml
```

## Dataset

Teacher games mix `HeuristicAgent`, `GreedyAgent`, and `RandomAgent`.
Independent processes write Zstandard-compressed Parquet shards. A complete
decision row stores the rules version, seed, player count, private
observation, legal actions, teacher choice, and final actor reward.

Train and validation splits are made by game seed, so decisions from one
episode cannot leak across splits.

## Model

`PolicyValueNetwork` combines:

- shared rank, suit, zone, and trump card embeddings;
- masked DeepSets pooling for the hand and table;
- a GRU for public action history;
- normalized global game features;
- a dynamic legal-action encoder;
- a policy head and a scalar value head.

The policy score is computed for every legal action. This supports variable
action counts and defense actions that also identify a table slot.

## PPO league

PPO starts from the best imitation checkpoint. Rollouts use:

- current-policy self-play;
- heuristic opponents;
- recent historical checkpoints.

Advantages are computed separately for each actor. Terminal rewards are
`+1` for first place, `-1` for the durak, and `0` for a middle place or draw.
No shaped reward is added for temporarily reducing the hand.

## Evaluation and release

Evaluation rotates the policy through every seat and reuses the same seeds
against random, greedy, and heuristic baselines. The report contains mean
reward, first-place rate, last-place rate, and game length.

Export writes:

```text
models/bot_v1.onnx
models/bot_v1_metadata.json
```

The exporter compares PyTorch and ONNX Runtime outputs before accepting the
model. The full configuration also requires a two-player win rate of at least
60% against the heuristic baseline. Metadata pins the rules, schema, encoder,
architecture, training step, metrics, promotion result, and SHA-256 digests.

If either release file is absent or incompatible, the live API uses
`HeuristicAgent`. This makes AI rooms playable before long GPU training is
finished and prevents a bad model artifact from stopping a game.
