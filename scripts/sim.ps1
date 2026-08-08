# Part B — KPI simulator helpers
# Usage:
#   .\scripts\sim.ps1 install
#   .\scripts\sim.ps1 run
#   .\scripts\sim.ps1 run-docker

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("install", "run", "run-docker", "help")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$SimDir = Join-Path $Root "apps\kpi-simulator"
$VenvPython = Join-Path $SimDir ".venv\Scripts\python.exe"
$VenvPip = Join-Path $SimDir ".venv\Scripts\pip.exe"

function Assert-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python 3.11+ is required and must be on PATH."
    }
}

switch ($Command) {
    "help" {
        Write-Host @"
Part B — KPI simulator
  .\scripts\sim.ps1 install     Create venv and install dependencies
  .\scripts\sim.ps1 run         Run simulator locally (needs Redpanda on localhost:19092)
  .\scripts\sim.ps1 run-docker  Run simulator container (needs docker compose profile sim)
"@
    }
    "install" {
        Assert-Python
        Set-Location $SimDir
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
        }
        & $VenvPip install -r requirements.txt
        if (-not (Test-Path "config.yaml")) {
            Copy-Item "config.example.yaml" "config.yaml"
        }
        Write-Host "Installed. Run: .\scripts\sim.ps1 run"
    }
    "run" {
        if (-not (Test-Path $VenvPython)) {
            Write-Error "Virtual env not found. Run: .\scripts\sim.ps1 install"
        }
        Set-Location $SimDir
        if (-not (Test-Path "config.yaml")) {
            Copy-Item "config.example.yaml" "config.yaml"
        }
        & $VenvPython -m kpi_simulator
    }
    "run-docker" {
        Set-Location $Root
        docker compose -f docker-compose.dev.yml --profile sim up -d --build kpi-simulator
        Write-Host "Simulator running in Docker. Metrics: http://localhost:9100/metrics"
    }
}
