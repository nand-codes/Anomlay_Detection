from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


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
    consumer_group: str = "ingest-worker"
    auto_offset_reset: str = "latest"

    database_url: str = "postgresql://netintel:netintel@localhost:5432/netintel"

    batch_size: int = 500
    batch_timeout_sec: float = 1.0
    poll_timeout_sec: float = 1.0

    metrics_port: int = 9101
    log_interval_sec: int = 10
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

    @field_validator("batch_size")
    @classmethod
    def _validate_batch_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("batch_size must be >= 1")
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
