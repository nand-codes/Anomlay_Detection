from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://netintel:netintel@localhost:5432/netintel"
    kafka_bootstrap: str = "localhost:19092"
    kpi_topic: str = "kpis.raw"
    redpanda_admin_url: str = "http://localhost:19644"
    host: str = "0.0.0.0"
    port: int = 8088


def load_settings() -> Settings:
    return Settings()
