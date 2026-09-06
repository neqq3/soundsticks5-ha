"""Privacy-preserving diagnostics."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import VERSION


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = entry.runtime_data
    state = coordinator.state
    return {
        "integration_version": VERSION,
        "options": {
            "preset_count": len(coordinator.presets),
        },
        "ble": {
            "available": coordinator.ble_available,
            "status": coordinator.ble_status,
            "rssi": coordinator.rssi,
            "last_error_type": coordinator.last_ble_error,
            "address": "REDACTED" if coordinator.ble_device else None,
        },
        "state": {
            "light_power": state.light_power,
            "brightness": state.brightness,
            "speed": state.speed,
            "theme_id": state.theme_id,
            "colors": state.colors,
            "playback": state.playback,
            "volume": state.volume,
            "track_title": "REDACTED" if state.track_title else None,
            "artist": "REDACTED" if state.artist else None,
            "feedback_tone": state.feedback_tone,
            "auto_off_configured": state.auto_off_configured,
            "auto_off_remaining": state.auto_off_remaining,
            "eq_gains_db": state.eq_gains_db,
            "unknown_36_raw": state.unknown_36,
        },
    }
