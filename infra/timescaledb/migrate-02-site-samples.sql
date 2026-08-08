-- Run on existing TimescaleDB volumes created before the interval-based redesign:
--   docker exec -i timescaledb psql -U netintel -d netintel < infra/timescaledb/migrate-02-site-samples.sql

CREATE TABLE IF NOT EXISTS kpi_site_samples (
    ts      TIMESTAMPTZ      NOT NULL,
    site    TEXT             NOT NULL,
    metric  TEXT             NOT NULL,
    value   DOUBLE PRECISION NOT NULL,
    UNIQUE (ts, site, metric)
);

SELECT create_hypertable('kpi_site_samples', 'ts', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_kpi_site_samples_site_metric_ts
    ON kpi_site_samples (site, metric, ts DESC);

SELECT add_retention_policy('kpi_site_samples', INTERVAL '365 days', if_not_exists => TRUE);
