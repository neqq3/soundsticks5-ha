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
    async_add_entities(
        [
            SoundSticksAutoOffRemaining(coordinator),
            SoundSticksOperatingState(coordinator),
            SoundSticksBleStatus(coordinator),
        ]
    )


class SoundSticksAutoOffRemaining(SoundSticksEntity, SensorEntity):
    _attr_translation_key = "auto_off_remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "auto_off_remaining")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.state.auto_off_remaining


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


class SoundSticksOperatingState(SoundSticksEntity, SensorEntity):
    """Conservative timer/media-derived state; not a physical-power claim."""

    _attr_translation_key = "operating_state"
    _attr_icon = "mdi:power-sleep"

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "operating_state")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return self.coordinator.operating_state

    @property
    def extra_state_attributes(self):
        return {
            "basis": "playback_and_auto_off_timer",
            "ble_control_available": self.coordinator.ble_available,
        }
