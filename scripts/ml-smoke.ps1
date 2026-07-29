$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

& $Python -m chinese_durak.ml.cli.benchmark `
  --games 100 `
  --players 2 `
  --agent heuristic
& $Python -m chinese_durak.ml.cli.generate_dataset `
  --config ml/configs/dataset-smoke.yaml
& $Python -m chinese_durak.ml.cli.train_imitation `
  --config ml/configs/imitation-smoke.yaml
& $Python -m chinese_durak.ml.cli.train_ppo `
  --config ml/configs/ppo-smoke.yaml
& $Python -m chinese_durak.ml.cli.evaluate `
  --config ml/configs/evaluation-smoke.yaml
& $Python -m chinese_durak.ml.cli.export `
  --config ml/configs/evaluation-smoke.yaml

Write-Host "ML smoke pipeline passed."
