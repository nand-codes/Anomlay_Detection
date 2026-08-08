# Step 1 / Part A — Redpanda setup

Local Kafka-compatible broker for the KPI simulator. Long-term KPI storage is **not** here; Redpanda is the in-flight buffer only.

## Prerequisites

- Docker Desktop (Windows) with Compose v2
- Enough RAM for one Redpanda node + Console (~2 GB free recommended)

## Quick start (PowerShell)

```powershell
copy .env.example .env
.\scripts\redpanda.ps1 up
.\scripts\redpanda.ps1 topics
.\scripts\redpanda.ps1 produce-smoke
.\scripts\redpanda.ps1 consume
```

Or with Make (Git Bash / WSL / Linux / macOS):

```bash
cp .env.example .env
make up
make topics
make produce-smoke
make consume
```

## Endpoints

| What | Address |
|------|---------|
| Kafka API (host clients) | `localhost:19092` |
| Kafka API (Compose network) | `redpanda-0:9092` |
| Redpanda Console | http://localhost:8080 |
| Admin API | http://localhost:19644 |

## Topic `kpis.raw`

| Setting | Value |
|---------|-------|
| Partitions | 12 (override with `KPI_TOPIC_PARTITIONS`) |
| Replication | 1 |
| Retention | 15 min by default (`900000` ms) — set in `config.yaml` / `KPI_TOPIC_RETENTION_MS` |

Create explicitly with `topics` — do not rely on auto-create for production-like behavior.

## Part A done when

1. `redpanda-0` is healthy
2. Topic `kpis.raw` exists and is describable
3. Smoke produce + consume works
4. Console shows the topic at http://localhost:8080

## Next (Part B)

Build `apps/kpi-simulator` publishing JSON KPIs to `kpis.raw` with partition key `device_id` and bootstrap `localhost:19092`.

## Tear down

```powershell
.\scripts\redpanda.ps1 down
```
