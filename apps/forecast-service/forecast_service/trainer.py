from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from .config import Settings
from .models import ForecastPoint, HistoryPoint, SeriesKey

logger = logging.getLogger(__name__)


def _naive_forecast(
    history: list[HistoryPoint],
    *,
    origin_ts: datetime,
    steps: int,
    interval_sec: int,
    residual_std: float,
) -> list[ForecastPoint]:
    last_value = history[-1].value
    std = residual_std if residual_std > 0 else max(abs(last_value) * 0.05, 0.01)
    points: list[ForecastPoint] = []
    for step in range(1, steps + 1):
        forecast_ts = origin_ts + timedelta(seconds=interval_sec * step)
        points.append(
            ForecastPoint(
                forecast_ts=forecast_ts,
                predicted_value=last_value,
                lower_bound=last_value - 1.96 * std,
                upper_bound=last_value + 1.96 * std,
            )
        )
    return points


def _fit_ets(
    history: list[HistoryPoint],
    settings: Settings,
) -> tuple[np.ndarray, float, str]:
    values = np.asarray([point.value for point in history], dtype=float)
    seasonal_periods = settings.seasonal_periods
    min_seasonal = seasonal_periods * 2

    if len(values) >= min_seasonal:
        try:
            model = ExponentialSmoothing(
                values,
                trend="add",
                seasonal="add",
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            )
            fit = model.fit(optimized=True)
            return fit.forecast(settings.horizon_steps), float(fit.sse ** 0.5 / max(len(values), 1)), "ets-seasonal-v1"
        except Exception as exc:
            logger.debug("Seasonal ETS failed for series length %d: %s", len(values), exc)

    try:
        model = ExponentialSmoothing(
            values,
            trend="add",
            seasonal=None,
            initialization_method="estimated",
        )
        fit = model.fit(optimized=True)
        return fit.forecast(settings.horizon_steps), float(fit.sse ** 0.5 / max(len(values), 1)), "ets-trend-v1"
    except Exception as exc:
        logger.debug("Trend ETS failed: %s", exc)
        residuals = np.diff(values) if len(values) > 1 else np.array([0.0])
        std = float(np.std(residuals)) if len(residuals) else 0.0
        return np.full(settings.horizon_steps, values[-1]), std, "naive-v1"


class ForecastTrainer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def forecast_series(
        self,
        key: SeriesKey,
        history: list[HistoryPoint],
        *,
        origin_ts: datetime | None = None,
    ) -> tuple[list[ForecastPoint], str]:
        if len(history) < self._settings.forecast_min_history_points:
            logger.warning(
                "Insufficient history for %s/%s (%d < %d) — using naive forecast",
                key.site,
                key.metric,
                len(history),
                self._settings.forecast_min_history_points,
            )
            origin = origin_ts or history[-1].ts
            return (
                _naive_forecast(
                    history,
                    origin_ts=origin,
                    steps=self._settings.horizon_steps,
                    interval_sec=self._settings.interval_sec,
                    residual_std=0.0,
                ),
                "naive-v1",
            )

        origin = origin_ts or history[-1].ts
        if origin.tzinfo is None:
            origin = origin.replace(tzinfo=timezone.utc)

        if self._settings.forecast_model.lower() == "ets":
            preds, residual_std, model_version = _fit_ets(history, self._settings)
        else:
            preds = np.full(self._settings.horizon_steps, history[-1].value)
            residual_std = float(pd.Series([p.value for p in history]).diff().dropna().std() or 0.0)
            model_version = "naive-v1"

        std = residual_std if residual_std > 0 else max(abs(float(preds[0])) * 0.05, 0.01)
        points: list[ForecastPoint] = []
        for step, predicted in enumerate(preds, start=1):
            forecast_ts = origin + timedelta(seconds=self._settings.interval_sec * step)
            value = float(predicted)
            points.append(
                ForecastPoint(
                    forecast_ts=forecast_ts,
                    predicted_value=value,
                    lower_bound=value - 1.96 * std,
                    upper_bound=value + 1.96 * std,
                )
            )
        return points, model_version
