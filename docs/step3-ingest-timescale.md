# Step 3 / Part C — Ingest Worker + TimescaleDB

Persist interval-based site KPIs from Redpanda into TimescaleDB.

## Architecture

```text
kpi-simulator (every 15 min) → Redpanda (kpis.raw) → ingest-worker → kpi_site_samples
```

## Table: `kpi_site_samples`

| Column | Example |
|--------|---------|
| `ts` | `2026-08-09 12:15:00+00` |
| `site` | `siteA` |
| `metric` | `latency_ms` |
| `value` | `52.3` |

Unique key: `(ts, site, metric)` — safe to replay the same bucket.

## Existing database?

If TimescaleDB was created before this redesign, run:

```powershell
Get-Content infra\timescaledb\migrate-02-site-samples.sql | docker exec -i timescaledb psql -U netintel -d netintel
```

## Run

```powershell
docker compose -f docker-compose.dev.yml up -d
.\scripts\ingest.ps1 install
.\scripts\ingest.ps1 run
```

## Verify

```powershell
.\scripts\ingest.ps1 query
```

Expected: rows at aligned timestamps (`12:00`, `12:15`, `12:30`, …).

## Seed demo history (for forecasting)

Before building the forecast service, load **2 days** of backfilled KPIs (same sites, metrics, 15-min buckets, diurnal patterns + fault injection):

```powershell
.\scripts\seed.ps1 install
.\scripts\seed.ps1 run          # default: 2 days
.\scripts\seed.ps1 run -Days 3    # optional: more history
```

This inserts ~2,880 rows (192 buckets × 15 KPIs). Existing live rows are kept (`ON CONFLICT DO NOTHING`).

## Part C done when

- [ ] Simulator publishes 15 KPIs per bucket
- [ ] Ingest writes to `kpi_site_samples`
- [ ] `SELECT * FROM kpi_site_samples ORDER BY ts DESC` shows aligned timestamps
