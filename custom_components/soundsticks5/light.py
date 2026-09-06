"""SoundSticks lighting entity (not a speaker power switch)."""

from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import build_brightness, build_light_power


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SoundSticksLight(entry.runtime_data)])


class SoundSticksLight(SoundSticksEntity, LightEntity):
    _attr_translation_key = "lighting"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "lighting")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.state.light_power

    @property
    def brightness(self) -> int | None:
        value = self.coordinator.state.brightness
        return None if value is None else round(value * 255 / 100)

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            value = round(int(kwargs[ATTR_BRIGHTNESS]) * 100 / 255)
            await self.coordinator.async_command(
                build_brightness(value),
                ack_command=0x33,
                state_update=lambda state: setattr(state, "brightness", value),
            )
        # Always send the idempotent power command. Notifications are not
        # guaranteed after every ACK, so a cached True must not suppress ON.
        await self.coordinator.async_command(
            build_light_power(True),
            ack_command=0x33,
            state_update=lambda state: setattr(state, "light_power", True),
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_command(
            build_light_power(False),
            ack_command=0x33,
            state_update=lambda state: setattr(state, "light_power", False),
        )
