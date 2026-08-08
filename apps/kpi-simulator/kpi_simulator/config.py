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

DEFAULT_INTERVAL_SEC = 900  # 15 minutes


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

    kafka_bootstrap: str = "localhost:19092"
    kpi_topic: str = "kpis.raw"

    sites: list[str] = Field(default_factory=lambda: ["siteA", "siteB", "siteC"])
    metrics: list[str] = Field(default_factory=lambda: list(DEFAULT_METRICS))

    # Simulation cadence — change to 300 (5 min) or 30 (30 sec) via config/env
    interval_sec: int = DEFAULT_INTERVAL_SEC
    align_to_boundary: bool = True

    fault_injection_rate: float = 0.05
    fault_duration_sec: int = 3600

    metrics_port: int = 9100
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
        # Env vars (e.g. Docker compose) override config.yaml defaults.
        return env_settings, dotenv_settings, init_settings, file_secret_settings

    @field_validator("sites", "metrics", mode="before")
    @classmethod
    def _split_csv(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("interval_sec")
    @classmethod
    def _validate_interval(cls, value: int) -> int:
        if value < 1:
            raise ValueError("interval_sec must be >= 1")
        return value

    @field_validator("fault_injection_rate")
    @classmethod
    def _validate_fault_rate(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("fault_injection_rate must be between 0 and 1")
        return value

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
