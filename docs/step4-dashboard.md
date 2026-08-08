# Step 4 — Unified Dashboard

Web UI for **Redpanda broker** and **TimescaleDB** KPI data.

## Open

**http://localhost:8088**

## Run locally

```powershell
docker compose -f docker-compose.dev.yml up -d
.\scripts\dashboard.ps1 install
.\scripts\dashboard.ps1 run
```

## Run in Docker

```powershell
.\scripts\dashboard.ps1 run-docker
```

## What you see

| Section | Shows |
|---------|--------|
| Summary cards | DB row count, broker message count, last bucket time |
| Redpanda broker | Health, topic partitions, offsets, message counts |
| TimescaleDB | Stats per site+metric, latest readings |
| KPI trend chart | Time series for selected site + metric |

Auto-refreshes every 30 seconds.

## Related UIs

| URL | Purpose |
|-----|---------|
| http://localhost:8088 | **This dashboard** (broker + DB) |
| http://localhost:8080 | Redpanda Console (raw topic browse) |

## API endpoints

- `GET /api/overview` — combined summary
- `GET /api/broker/overview` — Redpanda topic + health
- `GET /api/timescale/stats` — site/metric aggregates
- `GET /api/timescale/latest` — recent rows
- `GET /api/timescale/timeseries?site=siteA&metric=latency_ms` — chart data
