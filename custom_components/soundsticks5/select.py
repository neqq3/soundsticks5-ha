"""Theme and speed selectors for SoundSticks 5."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SPEED_BY_ID, SPEEDS, THEME_BY_ID, THEMES
from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import set_speed, set_theme


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SoundSticksCoordinator = entry.runtime_data
    async_add_entities([SoundSticksTheme(coordinator), SoundSticksSpeed(coordinator)])


class SoundSticksTheme(SoundSticksEntity, SelectEntity):
    _attr_name = "Theme"
    _attr_options = list(THEMES)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "theme")

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data or self.coordinator.data.theme_id is None:
            return None
        return THEME_BY_ID.get(self.coordinator.data.theme_id)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send(set_theme(option))


class SoundSticksSpeed(SoundSticksEntity, SelectEntity):
    _attr_name = "Speed"
    _attr_options = list(SPEEDS)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data or self.coordinator.data.speed is None:
            return None
        return SPEED_BY_ID.get(self.coordinator.data.speed)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send(set_speed(SPEEDS[option]))
