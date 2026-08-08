# Part A helpers for Windows (PowerShell) — Redpanda via docker compose
# Usage:
#   .\scripts\redpanda.ps1 up
#   .\scripts\redpanda.ps1 topics
#   .\scripts\redpanda.ps1 produce-smoke
#   .\scripts\redpanda.ps1 consume
#   .\scripts\redpanda.ps1 down

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("up", "down", "ps", "logs", "health", "topics", "produce-smoke", "consume", "help")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ComposeFile = "docker-compose.dev.yml"
$Compose = @("compose", "-f", $ComposeFile)
$Redpanda = "redpanda-0"
$Topic = if ($env:KPI_TOPIC) { $env:KPI_TOPIC } else { "kpis.raw" }
$Partitions = if ($env:KPI_TOPIC_PARTITIONS) { $env:KPI_TOPIC_PARTITIONS } else { "12" }
$RetentionMs = if ($env:KPI_TOPIC_RETENTION_MS) { $env:KPI_TOPIC_RETENTION_MS } else { "86400000" }

function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error @"
Docker is not installed or not on PATH.

Install Docker Desktop for Windows, start it, then re-run this script.
https://docs.docker.com/desktop/setup/install/windows-install/
"@
    }
}

function Invoke-Compose {
    param([string[]]$Args)
    & docker @Compose @Args
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed ($LASTEXITCODE)" }
}

function Wait-Healthy {
    Write-Host "Waiting for Redpanda healthy..."
    $deadline = (Get-Date).AddMinutes(2)
    do {
        try {
            $out = docker exec $Redpanda rpk cluster health 2>$null | Out-String
            if ($out -match "Healthy:\s+true") {
                docker exec $Redpanda rpk cluster health
                Write-Host "Bootstrap (host): localhost:19092"
                Write-Host "Console:          http://localhost:8080"
                return
            }
        } catch { }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Redpanda did not become healthy within 2 minutes"
}

Assert-Docker

switch ($Command) {
    "help" {
        Write-Host @"
Part A — Redpanda
  .\scripts\redpanda.ps1 up             Start Redpanda + Console
  .\scripts\redpanda.ps1 health         Wait until cluster is healthy
  .\scripts\redpanda.ps1 topics         Create $Topic (partitions=$Partitions)
  .\scripts\redpanda.ps1 produce-smoke  Produce one test message
  .\scripts\redpanda.ps1 consume        Consume sample messages
  .\scripts\redpanda.ps1 ps / logs      Status / follow logs
  .\scripts\redpanda.ps1 down           Stop and remove volumes
"@
    }
    "up" {
        if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
            Copy-Item ".env.example" ".env"
            Write-Host "Created .env from .env.example"
        }
        Invoke-Compose @("up", "-d")
        Wait-Healthy
    }
    "down" {
        Invoke-Compose @("down", "-v")
    }
    "ps" {
        Invoke-Compose @("ps")
    }
    "logs" {
        Invoke-Compose @("logs", "-f", "redpanda-0")
    }
    "health" {
        Wait-Healthy
    }
    "topics" {
        $create = docker exec $Redpanda rpk topic create $Topic -p $Partitions -r 1 --topic-config "retention.ms=$RetentionMs" 2>&1
        Write-Host $create
        docker exec $Redpanda rpk topic alter-config $Topic --set "retention.ms=$RetentionMs"
        if ($LASTEXITCODE -ne 0) { throw "Failed to set topic retention" }
        docker exec $Redpanda rpk topic list
        docker exec $Redpanda rpk topic describe $Topic
    }
    "produce-smoke" {
        $msg = '{"ts":"2026-08-08T00:00:00Z","device_id":"smoke-01","site":"lab","metric":"latency_ms","value":1.0}'
        $msg | docker exec -i $Redpanda rpk topic produce $Topic -k smoke-01
        if ($LASTEXITCODE -ne 0) { throw "produce failed" }
        Write-Host "Smoke message produced to $Topic"
    }
    "consume" {
        docker exec -it $Redpanda rpk topic consume $Topic -n 20
    }
}
