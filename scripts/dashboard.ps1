# Dashboard — unified Redpanda + TimescaleDB UI
# Usage:
#   .\scripts\dashboard.ps1 install
#   .\scripts\dashboard.ps1 run
#   .\scripts\dashboard.ps1 run-docker

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("install", "run", "run-docker", "help")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$AppDir = Join-Path $Root "apps\dashboard"
$VenvPython = Join-Path $AppDir ".venv\Scripts\python.exe"
$VenvPip = Join-Path $AppDir ".venv\Scripts\pip.exe"

switch ($Command) {
    "help" {
        Write-Host @"
Dashboard
  .\scripts\dashboard.ps1 install     Install dependencies
  .\scripts\dashboard.ps1 run         Run locally at http://localhost:8088
  .\scripts\dashboard.ps1 run-docker  Run in Docker
"@
    }
    "install" {
        Set-Location $AppDir
        if (-not (Test-Path ".venv")) { python -m venv .venv }
        & $VenvPip install -r requirements.txt
        Write-Host "Open http://localhost:8088 after: .\scripts\dashboard.ps1 run"
    }
    "run" {
        if (-not (Test-Path $VenvPython)) { Write-Error "Run install first" }
        Set-Location $AppDir
        & $VenvPython -m dashboard
    }
    "run-docker" {
        Set-Location $Root
        docker compose -f docker-compose.dev.yml up -d --build dashboard
        Write-Host "Dashboard: http://localhost:8088"
    }
}
