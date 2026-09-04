"""Color and seven App-scale EQ controls."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import EQ_FREQUENCIES
from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import build_color, build_eq, gain_db_to_app_eq_step


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([SoundSticksColor(coordinator), *(SoundSticksEq(coordinator, index, frequency) for index, frequency in enumerate(EQ_FREQUENCIES))])


class SoundSticksColor(SoundSticksEntity, NumberEntity):
    _attr_translation_key = "color_parameter"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "color")

    @property
    def native_value(self) -> float | None:
        theme_id = self.coordinator.state.theme_id
        return None if theme_id is None else self.coordinator.state.colors.get(theme_id)

    async def async_set_native_value(self, value: float) -> None:
        theme_id = self.coordinator.state.theme_id
        if theme_id is None:
            raise HomeAssistantError("Current lighting theme is unavailable; refresh state before setting color")
        await self.coordinator.async_command(build_color(theme_id, round(value)), ack_command=0x33)


class SoundSticksEq(SoundSticksEntity, NumberEntity):
    _attr_native_min_value = -12
    _attr_native_max_value = 12
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "step"
    _attr_icon = "mdi:tune-vertical"

    def __init__(self, coordinator: SoundSticksCoordinator, index: int, frequency: int) -> None:
        super().__init__(coordinator, f"eq_{frequency}")
        self._index = index
        self._frequency = frequency
        self._attr_name = f"EQ {frequency} Hz"

    @property
    def native_value(self) -> float | None:
        gains = self.coordinator.state.eq_gains_db
        return None if gains is None else gain_db_to_app_eq_step(self._index, gains[self._index])

    async def async_set_native_value(self, value: float) -> None:
        gains = self.coordinator.state.eq_gains_db
        if gains is None:
            raise HomeAssistantError("Current EQ snapshot is unavailable; refresh state before changing one band")
        steps = [gain_db_to_app_eq_step(index, gain) for index, gain in enumerate(gains)]
        steps[self._index] = round(value)
        await self.coordinator.async_command(build_eq(steps), ack_command=0xE3)
