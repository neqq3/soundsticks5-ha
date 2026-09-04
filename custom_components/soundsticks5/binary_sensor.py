"""Audio connection state."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SoundSticksCoordinator
from .entity import AudioBackendEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SoundSticksAudioConnected(entry.runtime_data)])


class SoundSticksAudioConnected(AudioBackendEntity, BinarySensorEntity):
    _attr_translation_key = "audio_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:bluetooth-audio"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "audio_connected")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.backend_status.get("audio_connected"))
