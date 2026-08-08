#!/usr/bin/env python3
"""Sync root config.yaml into .env and app-specific YAML files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "PyYAML is required. Run: .\\scripts\\sim.ps1 install"
    ) from exc

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
CONFIG_EXAMPLE = ROOT / "config.example.yaml"
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
SIM_CONFIG = ROOT / "apps" / "kpi-simulator" / "config.yaml"
SIM_EXAMPLE = ROOT / "apps" / "kpi-simulator" / "config.example.yaml"


def load_config() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE
    if not path.exists():
        raise SystemExit(f"No config file found. Copy {CONFIG_EXAMPLE.name} to config.yaml")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Config must be a mapping: {path}")
    return data


def retention_ms(config: dict) -> int:
    explicit = config.get("kpi_topic_retention_ms")
    if explicit is not None:
        return int(explicit)
    interval_sec = int(config.get("interval_sec", 900))
    return interval_sec * 1000


def upsert_env(lines: list[str], key: str, value: str) -> list[str]:
    pattern = re.compile(rf"^{re.escape(key)}=.*$")
    updated = False
    result: list[str] = []
    for line in lines:
        if pattern.match(line):
            result.append(f"{key}={value}")
            updated = True
        else:
            result.append(line)
    if not updated:
        if result and result[-1].strip():
            result.append("")
        result.append(f"{key}={value}")
    return result


def sync_env(config: dict) -> None:
    if not ENV_PATH.exists():
        if ENV_EXAMPLE.exists():
            ENV_PATH.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            ENV_PATH.write_text("", encoding="utf-8")

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    interval_sec = int(config.get("interval_sec", 900))
    updates = {
        "INTERVAL_SEC": str(interval_sec),
        "KPI_TOPIC_RETENTION_MS": str(retention_ms(config)),
        "KPI_TOPIC": str(config.get("kpi_topic", "kpis.raw")),
        "KPI_TOPIC_PARTITIONS": str(config.get("kpi_topic_partitions", 12)),
        "ALIGN_TO_BOUNDARY": "true" if config.get("align_to_boundary", True) else "false",
        "FAULT_INJECTION_RATE": str(config.get("fault_injection_rate", 0.05)),
        "FAULT_DURATION_SEC": str(config.get("fault_duration_sec", 3600)),
    }
    for key, value in updates.items():
        lines = upsert_env(lines, key, value)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_simulator_config(config: dict) -> None:
    if not SIM_CONFIG.exists():
        if SIM_EXAMPLE.exists():
            SIM_CONFIG.write_text(SIM_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            SIM_CONFIG.write_text("", encoding="utf-8")

    with SIM_CONFIG.open(encoding="utf-8") as handle:
        sim_data = yaml.safe_load(handle) or {}
    if not isinstance(sim_data, dict):
        sim_data = {}

    sim_data["interval_sec"] = int(config.get("interval_sec", 900))
    sim_data["align_to_boundary"] = bool(config.get("align_to_boundary", True))
    sim_data["kpi_topic"] = str(config.get("kpi_topic", sim_data.get("kpi_topic", "kpis.raw")))
    sim_data["fault_injection_rate"] = float(config.get("fault_injection_rate", 0.05))
    sim_data["fault_duration_sec"] = int(config.get("fault_duration_sec", 3600))

    with SIM_CONFIG.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(sim_data, handle, sort_keys=False, default_flow_style=False)


def main() -> int:
    config = load_config()
    sync_env(config)
    sync_simulator_config(config)
    interval = int(config.get("interval_sec", 900))
    retention = retention_ms(config)
    print(f"Synced config.yaml -> .env + apps/kpi-simulator/config.yaml")
    print(f"  interval_sec={interval} ({interval // 60} min)")
    print(f"  kpi_topic_retention_ms={retention} ({retention // 1000 // 60} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
