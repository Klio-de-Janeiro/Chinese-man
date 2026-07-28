$ErrorActionPreference = "Stop"

$LanAddress = Get-NetIPConfiguration |
    Where-Object { $null -ne $_.IPv4DefaultGateway } |
    Select-Object -ExpandProperty IPv4Address |
    Select-Object -ExpandProperty IPAddress -First 1

if (-not $LanAddress) {
    throw "Не удалось автоматически определить локальный IPv4-адрес."
}

Write-Host "Откройте на втором устройстве:"
Write-Host "http://${LanAddress}:3000"
Write-Host ""
Write-Host "Оба устройства должны находиться в одной локальной сети."
