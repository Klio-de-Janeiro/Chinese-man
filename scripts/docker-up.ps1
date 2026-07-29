$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$LanAddress = Get-NetIPConfiguration |
    Where-Object { $null -ne $_.IPv4DefaultGateway } |
    Select-Object -ExpandProperty IPv4Address |
    Select-Object -ExpandProperty IPAddress -First 1

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

if ($LanAddress) {
    $env:PUBLIC_GAME_HOST = $LanAddress
}

docker compose up --build --detach

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed to start. Check the error above."
}

docker compose ps

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose status check failed."
}

Write-Host ""
Write-Host "Game on this computer:"
Write-Host "  http://localhost:3000"

if ($LanAddress) {
    Write-Host ""
    Write-Host "Link for players on the local network:"
    Write-Host "  http://${LanAddress}:3000"
}
