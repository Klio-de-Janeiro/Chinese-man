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
docker compose ps

Write-Host ""
Write-Host "Игра на этом компьютере:"
Write-Host "  http://localhost:3000"

if ($LanAddress) {
    Write-Host ""
    Write-Host "Ссылка для игроков в локальной сети:"
    Write-Host "  http://${LanAddress}:3000"
}
