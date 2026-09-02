"""Per-theme color parameter for SoundSticks 5."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import THEMES
from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import set_color


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SoundSticksColor(entry.runtime_data)])


class SoundSticksColor(SoundSticksEntity, NumberEntity):
    _attr_name = "Color parameter"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = "slider"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "color")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or data.theme_id is None:
            return None
        return data.colors.get(data.theme_id)

    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data
        theme_id = data.theme_id if data and data.theme_id is not None else THEMES["ocean"][0]
        await self.coordinator.async_send(set_color(theme_id, round(value)))
