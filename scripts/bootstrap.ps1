$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $Python)) {
    py -3.12 -m venv .venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install --editable ".[dev]"
& $Python -m pip install --requirement apps/api/requirements.txt

Write-Host "Environment is ready."
