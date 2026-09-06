"""Safe reset, refresh and GATT-release buttons."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import THEMES
from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import build_color_reset


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SoundSticksRefreshState(coordinator),
            SoundSticksReleaseBle(coordinator),
            SoundSticksColorReset(coordinator),
            SoundSticksEqReset(coordinator),
        ]
    )


class SoundSticksColorReset(SoundSticksEntity, ButtonEntity):
    _attr_translation_key = "color_reset"
    _attr_icon = "mdi:palette-outline"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "color_reset")

    async def async_press(self) -> None:
        theme_id = self.coordinator.state.theme_id
        if theme_id is None:
            raise HomeAssistantError("Current lighting theme is unavailable; refresh state before resetting color")
        default_color = next(color for candidate, color in THEMES.values() if candidate == theme_id)
        await self.coordinator.async_command(
            build_color_reset(theme_id),
            ack_command=0x33,
            state_update=lambda state: state.colors.__setitem__(theme_id, default_color),
        )


class SoundSticksEqReset(SoundSticksEntity, ButtonEntity):
    _attr_translation_key = "eq_reset"
    _attr_icon = "mdi:tune-variant"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "eq_reset")

    async def async_press(self) -> None:
        await self.coordinator.async_set_eq([0] * 7)


class SoundSticksRefreshState(SoundSticksEntity, ButtonEntity):
    _attr_translation_key = "refresh_state"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "refresh_state")

    @property
    def available(self) -> bool:
        return self.coordinator.ble_device is not None

    async def async_press(self) -> None:
        await self.coordinator.async_refresh_state()


class SoundSticksReleaseBle(SoundSticksEntity, ButtonEntity):
    _attr_translation_key = "release_ble"
    _attr_icon = "mdi:bluetooth-off"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "release_ble")

    @property
    def available(self) -> bool:
        return self.coordinator.ble_device is not None

    async def async_press(self) -> None:
        await self.coordinator.async_release_ble()
