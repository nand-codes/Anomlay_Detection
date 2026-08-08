# Part C — ingest-worker helpers
# Usage:
#   .\scripts\ingest.ps1 install
#   .\scripts\ingest.ps1 run
#   .\scripts\ingest.ps1 run-docker
#   .\scripts\ingest.ps1 query

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("install", "run", "run-docker", "query", "help")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$IngestDir = Join-Path $Root "apps\ingest-worker"
$VenvPython = Join-Path $IngestDir ".venv\Scripts\python.exe"
$VenvPip = Join-Path $IngestDir ".venv\Scripts\pip.exe"

$PostgresUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "netintel" }
$PostgresDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "netintel" }

function Assert-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python 3.11+ is required and must be on PATH."
    }
}

switch ($Command) {
    "help" {
        Write-Host @"
Part C — ingest-worker
  .\scripts\ingest.ps1 install     Create venv and install dependencies
  .\scripts\ingest.ps1 run         Run ingest worker locally
  .\scripts\ingest.ps1 run-docker  Run ingest worker in Docker (profile ingest)
  .\scripts\ingest.ps1 query       Show row counts in TimescaleDB
"@
    }
    "install" {
        Assert-Python
        Set-Location $IngestDir
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
        }
        & $VenvPip install -r requirements.txt
        if (-not (Test-Path "config.yaml")) {
            Copy-Item "config.example.yaml" "config.yaml"
        }
        Write-Host "Installed. Ensure TimescaleDB is up, then: .\scripts\ingest.ps1 run"
    }
    "run" {
        if (-not (Test-Path $VenvPython)) {
            Write-Error "Virtual env not found. Run: .\scripts\ingest.ps1 install"
        }
        Set-Location $IngestDir
        if (-not (Test-Path "config.yaml")) {
            Copy-Item "config.example.yaml" "config.yaml"
        }
        & $VenvPython -m ingest_worker
    }
    "run-docker" {
        Set-Location $Root
        docker compose -f docker-compose.dev.yml --profile ingest up -d --build ingest-worker
        Write-Host "Ingest worker running in Docker. Metrics: http://localhost:9101/metrics"
    }
    "query" {
        Set-Location $Root
        docker exec timescaledb psql -U $PostgresUser -d $PostgresDb -c "SELECT count(*) AS kpi_site_samples FROM kpi_site_samples;"
        docker exec timescaledb psql -U $PostgresUser -d $PostgresDb -c "SELECT ts, site, metric, value FROM kpi_site_samples ORDER BY ts DESC LIMIT 15;"
        docker exec timescaledb psql -U $PostgresUser -d $PostgresDb -c "SELECT site, metric, count(*) AS rows, min(ts) AS first_ts, max(ts) AS last_ts FROM kpi_site_samples GROUP BY site, metric ORDER BY site, metric;"
    }
}
