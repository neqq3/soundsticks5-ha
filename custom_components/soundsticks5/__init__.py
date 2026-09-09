"""SoundSticks 5 Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import SoundSticksCoordinator
from .frontend import async_setup_frontend


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register the bundled card and integration services."""
    await async_setup_frontend(hass)

    def _coordinator() -> SoundSticksCoordinator:
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if getattr(entry, "runtime_data", None) is not None
        ]
        if not entries:
            raise ValueError("SoundSticks 5 is not loaded")
        return entries[0].runtime_data

    async def _save_preset(call: ServiceCall) -> None:
        coordinator = _coordinator()
        await coordinator.async_refresh_state()
        await coordinator.async_save_preset(call.data["name"])

    async def _apply_preset(call: ServiceCall) -> None:
        await _coordinator().async_apply_preset(call.data["name"])

    async def _delete_preset(call: ServiceCall) -> None:
        await _coordinator().async_delete_preset(call.data["name"])

    hass.services.async_register(DOMAIN, "save_preset", _save_preset)
    hass.services.async_register(DOMAIN, "apply_preset", _apply_preset)
    hass.services.async_register(DOMAIN, "delete_preset", _delete_preset)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # 1.1 retires the experimental audio backend. Remove its old registry
    # entries and options so upgrades do not leave unavailable controls on the
    # device page.
    registry = er.async_get(hass)
    retired_unique_ids = {
        "soundsticks5_audio_connected",
        "soundsticks5_wake",
        "soundsticks5_release_audio",
        "soundsticks5_backend_availability",
    }
    for entity_entry in list(registry.entities.values()):
        if entity_entry.config_entry_id == entry.entry_id and entity_entry.unique_id in retired_unique_ids:
            registry.async_remove(entity_entry.entity_id)
    retired_options = {key: value for key, value in entry.options.items() if not key.startswith("audio_") and key != "wake"}
    if retired_options != entry.options:
        hass.config_entries.async_update_entry(entry, options=retired_options)

    coordinator = SoundSticksCoordinator(hass, entry)
    entry.runtime_data = coordinator
    await coordinator.async_start()
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await coordinator.async_stop()
        raise
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: SoundSticksCoordinator = entry.runtime_data
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await coordinator.async_stop()
    return unloaded
