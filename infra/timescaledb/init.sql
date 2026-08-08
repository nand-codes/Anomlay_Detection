-- TimescaleDB schema — interval-based site-level KPIs (default 15-min buckets)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Primary store: one row per (bucket_ts, site, metric)
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

-- Forecast outputs (Part D)
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_ts     TIMESTAMPTZ      NOT NULL,
    generated_at    TIMESTAMPTZ      NOT NULL DEFAULT now(),
    site            TEXT             NOT NULL,
    metric          TEXT             NOT NULL,
    predicted_value DOUBLE PRECISION NOT NULL,
    lower_bound     DOUBLE PRECISION,
    upper_bound     DOUBLE PRECISION,
    horizon_minutes INTEGER          NOT NULL,
    model_version   TEXT             NOT NULL
);

SELECT create_hypertable('forecasts', 'forecast_ts', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_forecasts_site_metric_ts
    ON forecasts (site, metric, forecast_ts DESC);

-- Retention: site KPI samples 1 year (volume is small at 15-min cadence)
SELECT add_retention_policy('kpi_site_samples', INTERVAL '365 days', if_not_exists => TRUE);

-- Legacy high-volume table (deprecated — kept only if upgrading an older dev DB)
CREATE TABLE IF NOT EXISTS kpi_samples (
    ts          TIMESTAMPTZ      NOT NULL,
    device_id   TEXT             NOT NULL,
    site        TEXT             NOT NULL,
    metric      TEXT             NOT NULL,
    value       DOUBLE PRECISION NOT NULL
);
