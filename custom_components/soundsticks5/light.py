"""Lighting entity for SoundSticks 5."""

from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import set_brightness, set_light_power


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SoundSticksLight(entry.runtime_data)])


class SoundSticksLight(SoundSticksEntity, LightEntity):
    _attr_name = "Lighting"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "lighting")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.power if self.coordinator.data else None

    @property
    def brightness(self) -> int | None:
        if not self.coordinator.data or self.coordinator.data.brightness is None:
            return None
        return round(self.coordinator.data.brightness * 255 / 100)

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            value = round(int(kwargs[ATTR_BRIGHTNESS]) * 100 / 255)
            await self.coordinator.async_send(set_brightness(value))
        if not self.is_on:
            await self.coordinator.async_send(set_light_power(True))

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_send(set_light_power(False))
