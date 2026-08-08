# Seed TimescaleDB with historical demo KPI data (same structure as live simulator)
# Usage:
#   .\scripts\seed.ps1 install
#   .\scripts\seed.ps1 run              # default: 2 days at 15-min intervals
#   .\scripts\seed.ps1 run -Days 3
#   .\scripts\seed.ps1 query

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("install", "run", "query", "help")]
    [string]$Command,

    [int]$Days = 2
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$SimDir = Join-Path $Root "apps\kpi-simulator"
$VenvPython = Join-Path $SimDir ".venv\Scripts\python.exe"
$VenvPip = Join-Path $SimDir ".venv\Scripts\pip.exe"

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
Seed demo KPI history into TimescaleDB
  .\scripts\seed.ps1 install        Install simulator deps (includes psycopg)
  .\scripts\seed.ps1 run            Insert previous 2 days of 15-min site KPIs
  .\scripts\seed.ps1 run -Days 3    Custom history length
  .\scripts\seed.ps1 query            Show row counts and date range

Uses the same generator as kpi-simulator (sites, metrics, diurnal patterns, faults).
Existing rows are kept (ON CONFLICT DO NOTHING).
"@
    }
    "install" {
        Assert-Python
        Set-Location $SimDir
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
        }
        & $VenvPip install -r requirements.txt
        Write-Host "Installed. Run: .\scripts\seed.ps1 run"
    }
    "run" {
        if (-not (Test-Path $VenvPython)) {
            Write-Error "Virtual env not found. Run: .\scripts\seed.ps1 install"
        }
        Load-DotEnv
        if (-not $env:DATABASE_URL) {
            $env:DATABASE_URL = "postgresql://netintel:netintel@localhost:5432/netintel"
        }
        Set-Location $SimDir
        & $VenvPython -m kpi_simulator.backfill --days $Days
        Write-Host ""
        & (Join-Path $Root "scripts\seed.ps1") query
    }
    "query" {
        Set-Location $Root
        docker exec timescaledb psql -U $PostgresUser -d $PostgresDb -c "SELECT count(*) AS total_rows, count(DISTINCT ts) AS buckets, min(ts) AS first_ts, max(ts) AS last_ts FROM kpi_site_samples;"
        docker exec timescaledb psql -U $PostgresUser -d $PostgresDb -c "SELECT site, metric, count(*) AS rows, min(ts) AS first_ts, max(ts) AS last_ts FROM kpi_site_samples GROUP BY site, metric ORDER BY site, metric;"
    }
}
