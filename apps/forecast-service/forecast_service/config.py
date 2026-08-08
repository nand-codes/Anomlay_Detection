from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource

DEFAULT_METRICS = (
    "latency_ms",
    "packet_loss_pct",
    "cpu_pct",
    "interface_util_pct",
    "error_rate",
)


def _load_yaml_defaults(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a mapping: {path}")
    return data


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://netintel:netintel@localhost:5432/netintel"

    interval_sec: int = 900
    forecast_horizon_hours: int = 4
    forecast_min_history_points: int = 48
    forecast_model: str = "ets"
    forecast_history_limit: int = 672

    sites: list[str] = Field(default_factory=lambda: ["siteA", "siteB", "siteC"])
    metrics: list[str] = Field(default_factory=lambda: list(DEFAULT_METRICS))

    metrics_port: int = 9102
    run_once: bool = False
    config_file: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return env_settings, dotenv_settings, init_settings, file_secret_settings

    @field_validator("sites", "metrics", mode="before")
    @classmethod
    def _split_csv(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def horizon_steps(self) -> int:
        return max(1, int(self.forecast_horizon_hours * 3600 / self.interval_sec))

    @property
    def horizon_minutes(self) -> int:
        return self.forecast_horizon_hours * 60

    @property
    def seasonal_periods(self) -> int:
        return max(2, int(86400 / self.interval_sec))

    @classmethod
    def load(cls) -> "Settings":
        provisional = cls()
        yaml_path = Path(provisional.config_file) if provisional.config_file else None
        if yaml_path is None:
            for candidate in (Path("config.yaml"), Path("config.example.yaml")):
                if candidate.exists():
                    yaml_path = candidate
                    break
        defaults = _load_yaml_defaults(yaml_path)
        return cls(**defaults)


def load_settings() -> Settings:
    return Settings.load()
