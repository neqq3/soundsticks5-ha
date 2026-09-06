"""Device settings switches."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import build_feedback_tone


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SoundSticksFeedbackTone(entry.runtime_data)])


class SoundSticksFeedbackTone(SoundSticksEntity, SwitchEntity):
    _attr_translation_key = "feedback_tone"
    _attr_icon = "mdi:volume-medium"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "feedback_tone")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.state.feedback_tone

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_command(
            build_feedback_tone(True),
            response_command=0xF2,
            state_update=lambda state: setattr(state, "feedback_tone", True),
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_command(
            build_feedback_tone(False),
            response_command=0xF2,
            state_update=lambda state: setattr(state, "feedback_tone", False),
        )
