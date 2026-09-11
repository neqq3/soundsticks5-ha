"""Theme, speed and inactivity-timeout selectors."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import AUTO_OFF_BY_SECONDS, AUTO_OFF_SECONDS, SPEED_BY_ID, SPEEDS, THEME_BY_ID, THEMES
from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import build_speed, build_theme


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SoundSticksTheme(coordinator),
            SoundSticksSpeed(coordinator),
            SoundSticksAutoOff(coordinator),
            SoundSticksPreset(coordinator),
        ]
    )


class SoundSticksTheme(SoundSticksEntity, SelectEntity):
    _attr_translation_key = "theme"
    _attr_options = list(THEMES)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "theme")

    @property
    def current_option(self) -> str | None:
        return THEME_BY_ID.get(self.coordinator.state.theme_id)

    async def async_select_option(self, option: str) -> None:
        theme_id, default_color = THEMES[option]

        def update_state(state) -> None:
            state.theme_id = theme_id
            state.colors[theme_id] = default_color

        await self.coordinator.async_command(build_theme(option), ack_command=0x33, state_update=update_state)


class SoundSticksSpeed(SoundSticksEntity, SelectEntity):
    _attr_translation_key = "speed"
    _attr_options = list(SPEEDS)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def current_option(self) -> str | None:
        return SPEED_BY_ID.get(self.coordinator.state.speed)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_command(
            build_speed(option),
            ack_command=0x33,
            state_update=lambda state: setattr(state, "speed", SPEEDS[option]),
        )


class SoundSticksAutoOff(SoundSticksEntity, SelectEntity):
    _attr_translation_key = "auto_off"
    _attr_options = list(AUTO_OFF_SECONDS)

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "auto_off")

    @property
    def current_option(self) -> str | None:
        return AUTO_OFF_BY_SECONDS.get(self.coordinator.state.auto_off_configured)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_auto_off(option)


class SoundSticksPreset(SoundSticksEntity, SelectEntity):
    """User-defined, HA-persisted sound and lighting snapshots."""

    _attr_translation_key = "preset"
    _attr_icon = "mdi:bookmark-music-outline"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "preset")

    @property
    def available(self) -> bool:
        return True

    @property
    def options(self) -> list[str]:
        return sorted(self.coordinator.presets)

    @property
    def current_option(self) -> str | None:
        return self.coordinator.last_applied_preset

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_apply_preset(option)
