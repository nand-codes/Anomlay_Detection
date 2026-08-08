# Forecast service helpers
# Usage:
#   .\scripts\forecast.ps1 install
#   .\scripts\forecast.ps1 run-once
#   .\scripts\forecast.ps1 run
#   .\scripts\forecast.ps1 run-docker
#   .\scripts\forecast.ps1 query

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("install", "run", "run-once", "run-docker", "query", "help")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ForecastDir = Join-Path $Root "apps\forecast-service"
$VenvPython = Join-Path $ForecastDir ".venv\Scripts\python.exe"
$VenvPip = Join-Path $ForecastDir ".venv\Scripts\pip.exe"

$PostgresUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "netintel" }
$PostgresDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "netintel" }

function Assert-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python 3.11+ is required and must be on PATH."
    }
}

function Load-DotEnv {
    $envPath = Join-Path $Root ".env"
    if (-not (Test-Path $envPath)) { return }
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

switch ($Command) {
    "help" {
        Write-Host @"
Part D — forecast-service
  .\scripts\forecast.ps1 install     Create venv and install dependencies
  .\scripts\forecast.ps1 run-once    Run one forecast cycle locally
  .\scripts\forecast.ps1 run         Run scheduled forecast service locally
  .\scripts\forecast.ps1 run-docker  Run forecast service in Docker
  .\scripts\forecast.ps1 query       Show forecast row counts
"@
    }
    "install" {
        Assert-Python
        Set-Location $ForecastDir
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
        }
        & $VenvPip install -r requirements.txt
        if (-not (Test-Path "config.yaml")) {
            Copy-Item "config.example.yaml" "config.yaml"
        }
        Write-Host "Installed. Run: .\scripts\forecast.ps1 run-once"
    }
    "run-once" {
        if (-not (Test-Path $VenvPython)) {
            Write-Error "Virtual env not found. Run: .\scripts\forecast.ps1 install"
        }
        Load-DotEnv
        if (-not $env:DATABASE_URL) {
            $env:DATABASE_URL = "postgresql://netintel:netintel@localhost:5432/netintel"
        }
        $env:RUN_ONCE = "true"
        Set-Location $ForecastDir
        & $VenvPython -m forecast_service
    }
    "run" {
        if (-not (Test-Path $VenvPython)) {
            Write-Error "Virtual env not found. Run: .\scripts\forecast.ps1 install"
        }
        Load-DotEnv
        if (-not $env:DATABASE_URL) {
            $env:DATABASE_URL = "postgresql://netintel:netintel@localhost:5432/netintel"
        }
        $env:RUN_ONCE = "false"
        Set-Location $ForecastDir
        & $VenvPython -m forecast_service
    }
    "run-docker" {
        Set-Location $Root
        docker compose -f docker-compose.dev.yml --profile forecast up -d --build forecast-service
        Write-Host "Forecast service running in Docker. Metrics: http://localhost:9102/metrics"
    }
    "query" {
        Set-Location $Root
        docker exec timescaledb psql -U $PostgresUser -d $PostgresDb -c "SELECT count(*) AS forecast_rows, count(DISTINCT site || '/' || metric) AS series, max(generated_at) AS last_run FROM forecasts;"
        docker exec timescaledb psql -U $PostgresUser -d $PostgresDb -c "SELECT forecast_ts, site, metric, round(predicted_value::numeric, 2) AS predicted, model_version FROM forecasts ORDER BY generated_at DESC, site, metric, forecast_ts LIMIT 20;"
    }
}
