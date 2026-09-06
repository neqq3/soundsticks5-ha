"""SoundSticks 5 private-BLE media controls."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SoundSticksCoordinator
from .entity import SoundSticksEntity
from .protocol import build_media_action, build_volume


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SoundSticksMediaPlayer(entry.runtime_data)])


class SoundSticksMediaPlayer(SoundSticksEntity, MediaPlayerEntity):
    _attr_translation_key = "media_player"
    _attr_icon = "mdi:speaker-wireless"
    _attr_volume_step = 0.01

    def __init__(self, coordinator: SoundSticksCoordinator) -> None:
        super().__init__(coordinator, "media_player")

    @property
    def available(self) -> bool:
        return self.coordinator.ble_device is not None

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        return (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.VOLUME_SET
        )

    @property
    def state(self) -> MediaPlayerState | None:
        if self.coordinator.state.playback == 2:
            return MediaPlayerState.PLAYING
        if self.coordinator.state.playback == 1:
            return MediaPlayerState.PAUSED
        return MediaPlayerState.IDLE if self.available else None

    @property
    def volume_level(self) -> float | None:
        value = self.coordinator.state.volume
        return None if value is None else value / 100

    @property
    def media_title(self) -> str | None:
        return self.coordinator.state.track_title

    @property
    def media_artist(self) -> str | None:
        return self.coordinator.state.artist

    async def async_media_play(self) -> None:
        await self.coordinator.async_media_command(build_media_action("play"))

    async def async_media_pause(self) -> None:
        await self.coordinator.async_media_command(build_media_action("pause"))

    async def async_media_play_pause(self) -> None:
        await self.coordinator.async_toggle_playback()

    async def async_media_previous_track(self) -> None:
        await self.coordinator.async_media_command(build_media_action("previous"))

    async def async_media_next_track(self) -> None:
        await self.coordinator.async_media_command(build_media_action("next"))

    async def async_set_volume_level(self, volume: float) -> None:
        value = round(volume * 100)
        await self.coordinator.async_media_command(build_volume(value))
