"""Status and diagnostic sensors."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([SoundSticksAutoOffRemaining(coordinator), SoundSticksBackendAvailability(coordinator), SoundSticksBleStatus(coordinator)])


class SoundSticksAutoOffRemaining(SoundSticksEntity, SensorEntity):
    _attr_translation_key = "auto_off_remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "auto_off_remaining")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.state.auto_off_remaining


class SoundSticksBackendAvailability(SoundSticksEntity, SensorEntity):
    _attr_translation_key = "backend_availability"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:audio-video"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "backend_availability")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        if not self.coordinator.backend_enabled:
            return "disabled"
        return "available" if self.coordinator.backend_status.get("available") else "unavailable"


class SoundSticksBleStatus(SoundSticksEntity, SensorEntity):
    _attr_translation_key = "ble_connection"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "ble_connection")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return self.coordinator.ble_status

    @property
    def extra_state_attributes(self):
        return {"rssi": self.coordinator.rssi, "last_error_type": self.coordinator.last_ble_error}

