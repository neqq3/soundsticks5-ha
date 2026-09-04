"""SoundSticks 5 Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import SoundSticksCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
