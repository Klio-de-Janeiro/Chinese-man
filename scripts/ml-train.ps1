$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

& $Python -m chinese_durak.ml.cli.generate_dataset `
  --config ml/configs/dataset.yaml
& $Python -m chinese_durak.ml.cli.train_imitation `
  --config ml/configs/imitation.yaml
& $Python -m chinese_durak.ml.cli.train_ppo `
  --config ml/configs/ppo.yaml
& $Python -m chinese_durak.ml.cli.evaluate `
  --config ml/configs/evaluation.yaml
& $Python -m chinese_durak.ml.cli.export `
  --config ml/configs/evaluation.yaml

Write-Host "Training, evaluation, and ONNX export completed."
