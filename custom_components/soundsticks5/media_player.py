"""Unified BLE control and optional A2DP audio media player."""

from __future__ import annotations

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.components.media_player.browse_media import BrowseMedia, async_process_play_media_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_AUTO_RECONNECT, CONF_AUTO_RELEASE, CONF_RELEASE_DELAY, DEFAULT_RELEASE_DELAY
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
        return self.coordinator.ble_available or bool(self.coordinator.backend_status.get("available"))

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.VOLUME_SET
        )
        if self.coordinator.backend_status.get("available"):
            features |= MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.STOP | MediaPlayerEntityFeature.BROWSE_MEDIA
        return features

    @property
    def state(self) -> MediaPlayerState | None:
        if self.coordinator.backend_status.get("playing"):
            return MediaPlayerState.PLAYING
        if self.coordinator.backend_status.get("paused"):
            return MediaPlayerState.PAUSED
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
        if self.coordinator.backend_status.get("playing") or self.coordinator.backend_status.get("paused"):
            return self.coordinator.backend_status.get("title") or self.coordinator.state.track_title
        return self.coordinator.state.track_title

    @property
    def media_artist(self) -> str | None:
        return self.coordinator.state.artist

    async def async_media_play(self) -> None:
        if self.coordinator.backend_status.get("paused"):
            await self.coordinator.async_backend_action("resume")
            return
        await self.coordinator.async_command(build_media_action("play"), ack_command=0x43)

    async def async_media_pause(self) -> None:
        if self.coordinator.backend_status.get("playing"):
            await self.coordinator.async_backend_action("pause")
            return
        await self.coordinator.async_command(build_media_action("pause"), ack_command=0x43)

    async def async_media_previous_track(self) -> None:
        await self.coordinator.async_command(build_media_action("previous"), ack_command=0x43)

    async def async_media_next_track(self) -> None:
        await self.coordinator.async_command(build_media_action("next"), ack_command=0x43)

    async def async_set_volume_level(self, volume: float) -> None:
        value = round(volume * 100)
        if self.coordinator.ble_available:
            await self.coordinator.async_command(build_volume(value), ack_command=0x43)
        else:
            await self.coordinator.async_backend_action("volume", volume=value)

    async def async_play_media(self, media_type: str, media_id: str, **kwargs) -> None:
        if media_source.is_media_source_id(media_id):
            play_item = await media_source.async_resolve_media(self.hass, media_id, self.entity_id)
            media_id = async_process_play_media_url(self.hass, play_item.url)
            media_type = MediaType.MUSIC
        await self.coordinator.async_backend_action(
            "play",
            url=media_id,
            media_type=media_type,
            enqueue=kwargs.get("enqueue") not in (None, "replace", False),
            release_after_playback=self.coordinator.entry.options.get(CONF_AUTO_RELEASE, True),
            release_delay=self.coordinator.entry.options.get(CONF_RELEASE_DELAY, DEFAULT_RELEASE_DELAY),
            auto_reconnect=self.coordinator.entry.options.get(CONF_AUTO_RECONNECT, True),
        )

    async def async_media_stop(self) -> None:
        await self.coordinator.async_backend_action("stop")

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )
