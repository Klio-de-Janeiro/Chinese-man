$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Bin = Join-Path $ProjectRoot ".venv\Scripts"
$CMake = Join-Path $Bin "cmake.exe"
$CTest = Join-Path $Bin "ctest.exe"
$Python = Join-Path $Bin "python.exe"

Set-Location $ProjectRoot

& $CMake --preset native-debug
& $CMake --build --preset native-debug
& $CTest --preset native-debug
& $Python -m pytest
& $Python -m ruff check python apps/api
npm run lint
npm run test

Write-Host "All checks passed."
