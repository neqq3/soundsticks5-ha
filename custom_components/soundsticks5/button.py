"""Safe reset, wake and release buttons."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_RELEASE_DELAY, CONF_WAKE_BEHAVIOR, DEFAULT_RELEASE_DELAY, DEFAULT_WAKE_BEHAVIOR
from .coordinator import SoundSticksCoordinator
from .entity import AudioBackendEntity, SoundSticksEntity
from .protocol import build_color_reset, build_eq_reset


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([SoundSticksColorReset(coordinator), SoundSticksEqReset(coordinator), SoundSticksWake(coordinator), SoundSticksRelease(coordinator)])


class SoundSticksColorReset(SoundSticksEntity, ButtonEntity):
    _attr_translation_key = "color_reset"
    _attr_icon = "mdi:palette-outline"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "color_reset")

    async def async_press(self) -> None:
        theme_id = self.coordinator.state.theme_id
        if theme_id is None:
            raise HomeAssistantError("Current lighting theme is unavailable; refresh state before resetting color")
        await self.coordinator.async_command(build_color_reset(theme_id), ack_command=0x33)


class SoundSticksEqReset(SoundSticksEntity, ButtonEntity):
    _attr_translation_key = "eq_reset"
    _attr_icon = "mdi:tune-variant"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "eq_reset")

    async def async_press(self) -> None:
        await self.coordinator.async_command(build_eq_reset(), ack_command=0xE3)


class SoundSticksWake(AudioBackendEntity, ButtonEntity):
    _attr_translation_key = "wake"
    _attr_icon = "mdi:power-on"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "wake")

    async def async_press(self) -> None:
        options = self.coordinator.entry.options
        behavior = options.get(CONF_WAKE_BEHAVIOR, DEFAULT_WAKE_BEHAVIOR)
        delay = options.get(CONF_RELEASE_DELAY, DEFAULT_RELEASE_DELAY)
        if behavior == "wake_release":
            await self.coordinator.async_backend_action("wake-release", delay=delay)
        elif behavior == "wake_only":
            await self.coordinator.async_backend_action("wake-release", delay=0)
        else:
            await self.coordinator.async_backend_action("wake", keep_connected=True)


class SoundSticksRelease(AudioBackendEntity, ButtonEntity):
    _attr_translation_key = "release_audio"
    _attr_icon = "mdi:bluetooth-off"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "release_audio")

    async def async_press(self) -> None:
        await self.coordinator.async_backend_action("disconnect")
