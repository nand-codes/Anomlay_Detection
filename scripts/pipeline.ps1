# Start/stop the full KPI pipeline (simulator -> Redpanda -> ingest -> TimescaleDB)
# Usage:
#   .\scripts\pipeline.ps1 sync      Apply config.yaml to .env + simulator config
#   .\scripts\pipeline.ps1 topics    Create/update kpis.raw retention from config
#   .\scripts\pipeline.ps1 start     Sync config, ensure infra, start sim + ingest
#   .\scripts\pipeline.ps1 stop      Stop simulator and ingest worker
#   .\scripts\pipeline.ps1 status     Show service status and row counts

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("sync", "topics", "start", "stop", "status", "help")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ComposeFile = "docker-compose.dev.yml"
$Compose = @("compose", "-f", $ComposeFile)
$Redpanda = "redpanda-0"
$SimDir = Join-Path $Root "apps\kpi-simulator"
$VenvPython = Join-Path $SimDir ".venv\Scripts\python.exe"

function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is required. Install Docker Desktop and retry."
    }
}

function Load-DotEnv {
    if (-not (Test-Path ".env")) { return }
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

function Ensure-ConfigYaml {
    if (-not (Test-Path "config.yaml")) {
        Copy-Item "config.example.yaml" "config.yaml"
        Write-Host "Created config.yaml from config.example.yaml"
    }
}

function Invoke-SyncConfig {
    Ensure-ConfigYaml
    $python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }
    & $python (Join-Path $Root "scripts\sync_config.py")
    if ($LASTEXITCODE -ne 0) { throw "sync_config.py failed" }
    Load-DotEnv
}

function Invoke-Topics {
    $topic = if ($env:KPI_TOPIC) { $env:KPI_TOPIC } else { "kpis.raw" }
    $partitions = if ($env:KPI_TOPIC_PARTITIONS) { $env:KPI_TOPIC_PARTITIONS } else { "12" }
    $retentionMs = if ($env:KPI_TOPIC_RETENTION_MS) { $env:KPI_TOPIC_RETENTION_MS } else { "900000" }

    docker exec $Redpanda rpk topic create $topic -p $partitions -r 1 --topic-config "retention.ms=$retentionMs" 2>&1 | Out-Host
    docker exec $Redpanda rpk topic alter-config $topic --set "retention.ms=$retentionMs" 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Failed to set topic retention" }
    docker exec $Redpanda rpk topic describe $topic
}

switch ($Command) {
    "help" {
        Write-Host @"
NetIntel pipeline
  .\scripts\pipeline.ps1 sync     Apply config.yaml -> .env + simulator config
  .\scripts\pipeline.ps1 topics   Create/update Redpanda topic retention
  .\scripts\pipeline.ps1 start    Full start (infra + sim + ingest)
  .\scripts\pipeline.ps1 stop     Stop simulator and ingest worker
  .\scripts\pipeline.ps1 status   Show running services and DB counts

Edit config.yaml (interval_sec, retention) then run sync or start.
"@
    }
    "sync" {
        if (-not (Test-Path $VenvPython)) {
            Write-Host "Simulator venv not found - installing..."
            & (Join-Path $Root "scripts\sim.ps1") install
        }
        Invoke-SyncConfig
    }
    "topics" {
        Assert-Docker
        Invoke-SyncConfig
        Invoke-Topics
    }
    "start" {
        Assert-Docker
        if (-not (Test-Path $VenvPython)) {
            & (Join-Path $Root "scripts\sim.ps1") install
        }
        Invoke-SyncConfig

        & docker @Compose up -d redpanda-0 console timescaledb dashboard
        if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

        Write-Host "Waiting for Redpanda healthy..."
        & (Join-Path $Root "scripts\redpanda.ps1") health

        Invoke-Topics

        & docker @Compose --profile sim --profile ingest --profile forecast up -d --build kpi-simulator ingest-worker forecast-service dashboard
        if ($LASTEXITCODE -ne 0) { throw "Failed to start simulator/ingest/forecast" }

        $intervalMin = [int]($env:INTERVAL_SEC / 60)
        $retentionMin = [int]($env:KPI_TOPIC_RETENTION_MS / 60000)
        Write-Host ""
        Write-Host "Pipeline started."
        Write-Host ('  interval_sec:        {0} ({1} min)' -f $env:INTERVAL_SEC, $intervalMin)
        Write-Host ('  topic retention_ms:  {0} ({1} min)' -f $env:KPI_TOPIC_RETENTION_MS, $retentionMin)
        Write-Host "  Dashboard:           http://localhost:8088"
        Write-Host "  Redpanda Console:    http://localhost:8080"
        Write-Host "  Simulator metrics:   http://localhost:9100/metrics"
        Write-Host "  Ingest metrics:      http://localhost:9101/metrics"
        Write-Host "  Forecast metrics:    http://localhost:9102/metrics"
    }
    "stop" {
        Assert-Docker
        & docker @Compose --profile sim --profile ingest --profile forecast stop kpi-simulator ingest-worker forecast-service
        Write-Host "Stopped simulator, ingest worker, and forecast service."
    }
    "status" {
        Assert-Docker
        Load-DotEnv
        & docker @Compose ps
        Write-Host ""
        Write-Host "Config: interval_sec=$($env:INTERVAL_SEC), retention_ms=$($env:KPI_TOPIC_RETENTION_MS)"
        & (Join-Path $Root 'scripts\ingest.ps1') query
    }
}
