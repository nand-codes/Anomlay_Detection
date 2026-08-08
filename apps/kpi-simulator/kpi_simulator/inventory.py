from __future__ import annotations

from dataclasses import dataclass

from .config import Settings


@dataclass(frozen=True, slots=True)
class Device:
    device_id: str
    site: str
    seed: int


def build_inventory(settings: Settings) -> list[Device]:
    devices: list[Device] = []
    sites = settings.sites or ["siteA"]
    for index in range(settings.num_devices):
        site = sites[index % len(sites)]
        device_num = (index // len(sites)) + 1
        device_id = f"router-{site}-{device_num:02d}"
        devices.append(Device(device_id=device_id, site=site, seed=index + 1))
    return devices
