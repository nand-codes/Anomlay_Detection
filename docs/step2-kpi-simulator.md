# Step 2 / Part B — KPI Simulator (interval-based)

Publishes **site-level** KPI events to Redpanda on a configurable interval (default **every 15 minutes**).

## Behavior

- At each bucket (`12:00`, `12:15`, `12:30`, …) emits **one KPI per site × metric**
- Default: 3 sites × 5 metrics = **15 messages every 15 minutes**
- Timestamps are aligned to wall-clock bucket boundaries

## Configuration

Edit root **`config.yaml`** (copy from `config.example.yaml`), then run `.\scripts\pipeline.ps1 sync`.

| Setting | Default | Example |
|---------|---------|---------|
| `interval_sec` | `900` (15 min) | `300` = 5 min, `30` = 30 sec |
| `kpi_topic_retention_ms` | `interval_sec × 1000` | Redpanda buffer retention |
| `align_to_boundary` | `true` | Align ts to 12:00, 12:15, … |
| `sites` | siteA, siteB, siteC | In `apps/kpi-simulator/config.yaml` |
| `metrics` | 5 network KPIs | latency_ms, cpu_pct, … |

```yaml
interval_sec: 900
align_to_boundary: true
# kpi_topic_retention_ms: 900000   # optional override
```

**Dev tip:** use `interval_sec: 30` or `60` for faster testing.

## Message format

```json
{
  "ts": "2026-08-09T12:15:00Z",
  "site": "siteA",
  "metric": "latency_ms",
  "value": 52.3
}
```

## Run

```powershell
.\scripts\sim.ps1 install
.\scripts\sim.ps1 run
```

## Storage impact (1 month)

~15 rows × 96 buckets/day × 30 days ≈ **43,200 rows** (~5 MB) — very light.
