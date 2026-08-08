# Step 5 / Part D — Forecast Service

Predict **4 hours ahead** for each site+metric using historical KPIs from TimescaleDB.

## Architecture

```text
kpi_site_samples (history) → forecast-service → forecasts table → dashboard chart
```

## Configuration (`config.yaml`)

| Setting | Default | Description |
|---------|---------|-------------|
| `forecast_horizon_hours` | `4` | Prediction horizon |
| `forecast_min_history_points` | `48` | Min buckets before ETS (~12h at 15 min) |
| `forecast_model` | `ets` | `ets` (Exponential Smoothing) or falls back to naive |

At 15-min intervals, 4h = **16 forecast points** per series × **15 series** = **240 rows** per run.

## Prerequisites

Load at least ~2 days of history:

```powershell
.\scripts\seed.ps1 run
```

## Run once (local)

```powershell
.\scripts\forecast.ps1 install
.\scripts\forecast.ps1 run-once
.\scripts\forecast.ps1 query
```

## Run scheduled (Docker)

```powershell
.\scripts\forecast.ps1 run-docker
```

Runs immediately on startup, then every `interval_sec` (15 min).

## Verify

```powershell
.\scripts\forecast.ps1 query
```

Expected: `240` forecast rows (15 series × 16 horizon steps).

Dashboard: http://localhost:8088 — KPI trend chart shows **blue = actual**, **orange dashed = forecast**.

## Table: `forecasts`

| Column | Description |
|--------|-------------|
| `forecast_ts` | Predicted bucket time |
| `generated_at` | When the model ran |
| `site`, `metric` | Series key |
| `predicted_value` | Forecast |
| `lower_bound`, `upper_bound` | ~95% interval |
| `horizon_minutes` | `240` (4h) |
| `model_version` | e.g. `ets-seasonal-v1` |

## Part D done when

- [ ] `forecasts` table has rows after `run-once`
- [ ] Dashboard shows actual + forecast overlay
- [ ] Scheduled service runs in Docker without errors

## Next

Part E — Anomaly detection (Isolation Forest) using fault-injected KPI spikes.
