"""Theme, speed and inactivity-timeout selectors."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import AUTO_OFF_BY_SECONDS, AUTO_OFF_SECONDS, SPEED_BY_ID, SPEEDS, THEME_BY_ID, THEMES
from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import build_auto_off, build_speed, build_theme


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([SoundSticksTheme(coordinator), SoundSticksSpeed(coordinator), SoundSticksAutoOff(coordinator)])


class SoundSticksTheme(SoundSticksEntity, SelectEntity):
    _attr_translation_key = "theme"
    _attr_options = list(THEMES)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "theme")

    @property
    def current_option(self) -> str | None:
        return THEME_BY_ID.get(self.coordinator.state.theme_id)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_command(build_theme(option), ack_command=0x33)


class SoundSticksSpeed(SoundSticksEntity, SelectEntity):
    _attr_translation_key = "speed"
    _attr_options = list(SPEEDS)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def current_option(self) -> str | None:
        return SPEED_BY_ID.get(self.coordinator.state.speed)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_command(build_speed(option), ack_command=0x33)


class SoundSticksAutoOff(SoundSticksEntity, SelectEntity):
    _attr_translation_key = "auto_off"
    _attr_options = list(AUTO_OFF_SECONDS)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "auto_off")

    @property
    def current_option(self) -> str | None:
        return AUTO_OFF_BY_SECONDS.get(self.coordinator.state.auto_off_configured)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_command(build_auto_off(option), ack_command=0xBA)
