# KPI Simulator

Interval-based **site-level** network KPI publisher for Redpanda topic `kpis.raw`.

## Defaults

- **Every 15 minutes** (`interval_sec: 900`)
- Aligned timestamps: `12:00`, `12:15`, `12:30`, …
- 3 sites × 5 metrics = **15 messages per bucket**

## Change interval

`config.yaml` or environment:

```yaml
interval_sec: 300   # 5 minutes
# interval_sec: 30  # 30 seconds (dev only)
```

```powershell
$env:INTERVAL_SEC = "60"
.\scripts\sim.ps1 run
```

## Quick start

```powershell
.\scripts\sim.ps1 install
.\scripts\sim.ps1 run
```

See [docs/step2-kpi-simulator.md](../../docs/step2-kpi-simulator.md).
