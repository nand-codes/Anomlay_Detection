# Enterprise AI Network Intelligence Platform

Greenfield MLOps platform for simulated network KPI streaming, anomaly detection, forecasting, and RAG RCA.

**Simulation cadence:** site-level KPIs every **15 minutes** — set in root `config.yaml` (`interval_sec: 900`).

## Current status

| Part | Status | Docs |
|------|--------|------|
| A — Redpanda | Done | [docs/step1-redpanda.md](docs/step1-redpanda.md) |
| B — KPI simulator | Done | [docs/step2-kpi-simulator.md](docs/step2-kpi-simulator.md) |
| C — Ingest + TimescaleDB | Done | [docs/step3-ingest-timescale.md](docs/step3-ingest-timescale.md) |
| Dashboard | Done | [docs/step4-dashboard.md](docs/step4-dashboard.md) |

## Quick start (Windows)

**One-command pipeline** (simulator + ingest + 15 min retention):
```powershell
copy config.example.yaml config.yaml   # edit interval_sec if needed
.\scripts\pipeline.ps1 start
```

**Or manual steps:**
```powershell
copy .env.example .env
docker compose -f docker-compose.dev.yml up -d
.\scripts\pipeline.ps1 sync
.\scripts\pipeline.ps1 topics
```

**Run pipeline locally (without Docker for sim/ingest):**
```powershell
# Terminal 1 — simulator
.\scripts\sim.ps1 run

# Terminal 2 — ingest worker
.\scripts\ingest.ps1 install
.\scripts\ingest.ps1 run

# Terminal 3 — verify DB
.\scripts\ingest.ps1 query
```

## Endpoints

- Redpanda Console: http://localhost:8080
- Simulator metrics: http://localhost:9100/metrics
- Ingest metrics: http://localhost:9101/metrics
- **Dashboard:** http://localhost:8088
- TimescaleDB: `localhost:5432` (user/pass/db: `netintel`)

## Next

Part D: forecast-service (4h ahead per site+metric using `site_metric_1min`)
