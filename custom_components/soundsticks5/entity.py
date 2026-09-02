"""Shared entity base for SoundSticks 5."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import SoundSticksCoordinator


class SoundSticksEntity(CoordinatorEntity[SoundSticksCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SoundSticksCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"soundsticks5_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "soundsticks5")},
            name=NAME,
            manufacturer="Harman Kardon",
            model="SoundSticks 5",
        )
