"""BLE coordinator for SoundSticks 5."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from typing import Any

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothChange, BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AUTO_OFF_BY_SECONDS,
    BLE_IDLE_DISCONNECT_SECONDS,
    COMMAND_UUID,
    CONTROL_SERVICE_UUID,
    FAST_PAIR_UUID,
    HARMAN_DISCOVERY_UUID,
    NAME,
    NOTIFY_UUID,
    PRESETS_OPTION,
    QUERY_AGGREGATE,
    QUERY_AUTO_OFF,
    QUERY_EQ,
    QUERY_FEEDBACK,
    QUERY_LIGHT,
    SPEED_BY_ID,
    THEME_BY_ID,
)
from .discovery import matches_soundsticks5_advertisement
from .protocol import (
    DeviceState,
    Frame,
    ProtocolError,
    app_eq_step_to_gain_db,
    apply_notification,
    build_auto_off,
    build_brightness,
    build_color,
    build_eq,
    build_feedback_tone,
    build_light_power,
    build_media_action,
    build_speed,
    build_theme,
    build_volume,
    gain_db_to_app_eq_step,
)

_LOGGER = logging.getLogger(__name__)
WaitPredicate = Callable[[Frame], bool]
StateUpdater = Callable[[DeviceState], None]


class SoundSticksCoordinator(DataUpdateCoordinator[DeviceState]):
    """Own serialized GATT I/O and the confirmed device-state cache."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        # After one startup snapshot, notifications and explicit commands own
        # BLE state. A periodic full refresh caused proxy-side connection
        # storms and made commands wait behind failed polls.
        super().__init__(hass, _LOGGER, name=NAME, update_interval=None)
        self.entry = entry
        self.state = DeviceState()
        self.ble_device: BLEDevice | None = None
        self.ble_available = False
        self.ble_status = "not_seen"
        self.last_ble_error: str | None = None
        self.rssi: int | None = None
        self._client: BleakClient | None = None
        self._disconnect_task: asyncio.Task[None] | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._io_lock = asyncio.Lock()
        self._waiters: list[tuple[WaitPredicate, asyncio.Future[Frame]]] = []
        self._eq_revision = 0
        self._desired_eq_steps: list[int] | None = None
        self.last_applied_preset: str | None = None

    @property
    def presets(self) -> dict[str, dict[str, Any]]:
        """Return sanitized persisted presets."""
        raw = self.entry.options.get(PRESETS_OPTION, {})
        return raw if isinstance(raw, dict) else {}

    @property
    def operating_state(self) -> str:
        """Return a conservative activity state, not a physical power claim."""
        if self.state.playback == 2 or (self.state.auto_off_remaining or 0) > 0:
            return "active"
        if (
            self.state.auto_off_configured not in (None, 0)
            and self.state.auto_off_remaining == 0
        ):
            return "standby"
        return "unknown"

    async def async_start(self) -> None:
        """Start watching advertisements without retaining an RPA as identity."""
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            if self._matches_advertisement(info):
                self._remember(info)
                break

        @callback
        def _on_bluetooth(info: BluetoothServiceInfoBleak, _change: BluetoothChange) -> None:
            if self._matches_advertisement(info):
                self._remember(info)

        for matcher in (
            {"service_uuid": CONTROL_SERVICE_UUID, "connectable": True},
            {"service_uuid": HARMAN_DISCOVERY_UUID, "connectable": True},
            {"service_data_uuid": FAST_PAIR_UUID, "connectable": True},
        ):
            self._unsubs.append(
                bluetooth.async_register_callback(
                    self.hass,
                    _on_bluetooth,
                    matcher,
                    bluetooth.BluetoothScanningMode.ACTIVE,
                )
            )

    def _matches_advertisement(self, info: BluetoothServiceInfoBleak) -> bool:
        return matches_soundsticks5_advertisement(info.name, info.service_uuids, info.service_data)

    @callback
    def _remember(self, info: BluetoothServiceInfoBleak) -> None:
        became_available = not self.ble_available
        self.ble_device = info.device
        self.rssi = info.rssi
        self.ble_available = True
        if self.ble_status == "not_seen":
            self.ble_status = "advertising"
        if became_available:
            self.async_update_listeners()

    async def async_stop(self) -> None:
        for unsubscribe in self._unsubs:
            unsubscribe()
        self._unsubs.clear()
        self._cancel_scheduled_disconnect()
        async with self._io_lock:
            await self._disconnect()

    def _cancel_scheduled_disconnect(self) -> None:
        task, self._disconnect_task = self._disconnect_task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    def _schedule_disconnect(self) -> None:
        """Release an idle GATT session without breaking a command burst."""
        self._cancel_scheduled_disconnect()
        self._disconnect_task = self.hass.async_create_task(
            self._disconnect_after_idle(),
            "soundsticks5 idle BLE disconnect",
        )

    async def _disconnect_after_idle(self) -> None:
        try:
            await asyncio.sleep(BLE_IDLE_DISCONNECT_SECONDS)
            async with self._io_lock:
                await self._disconnect()
                self.async_update_listeners()
        except asyncio.CancelledError:
            return
        finally:
            if self._disconnect_task is asyncio.current_task():
                self._disconnect_task = None

    async def _disconnect(self) -> None:
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            try:
                await client.disconnect()
            except Exception as exc:  # pragma: no cover - adapter dependent
                _LOGGER.debug("BLE disconnect failed: %s", type(exc).__name__)
        self.ble_status = "advertising" if self.ble_device else "not_seen"

    async def async_release_ble(self) -> None:
        """Immediately release this integration's GATT control session."""
        self._cancel_scheduled_disconnect()
        async with self._io_lock:
            await self._disconnect()
        self.async_update_listeners()

    def _disconnected(self, client: BleakClient) -> None:
        self.hass.loop.call_soon_threadsafe(self._mark_disconnected, client)

    @callback
    def _mark_disconnected(self, client: BleakClient) -> None:
        # A stale callback from a client disposed during RPA rotation must not
        # overwrite the state of a newer connection.
        if self._client is not client:
            return
        self._client = None
        self.ble_status = "advertising" if self.ble_device else "not_seen"
        self.async_update_listeners()

    async def _ensure_connected(self) -> BleakClient:
        self._cancel_scheduled_disconnect()
        if self.ble_device is None:
            raise UpdateFailed("speaker has not been seen by Home Assistant Bluetooth")
        if self._client is not None and self._client.is_connected:
            # A later advertisement may carry a new RPA while the current
            # connection is still valid. Keep the live link authoritative.
            return self._client
        if self._client is not None:
            await self._disconnect()
        self.ble_status = "connecting"
        client = await establish_connection(
            BleakClient,
            self.ble_device,
            NAME,
            disconnected_callback=self._disconnected,
            max_attempts=1,
        )
        try:
            services = {str(service.uuid).lower() for service in client.services}
            if CONTROL_SERVICE_UUID not in services:
                raise UpdateFailed("candidate does not expose the private SoundSticks control service")
            await client.start_notify(NOTIFY_UUID, self._notify_from_bleak)
        except Exception:
            # establish_connection returns an already-connected client.  Do
            # not leak that link if identity verification or CCCD setup fails.
            if client.is_connected:
                await client.disconnect()
            raise
        self._client = client
        self.ble_status = "connected"
        self.last_ble_error = None
        return client

    def _notify_from_bleak(self, _sender: Any, data: bytearray) -> None:
        self.hass.loop.call_soon_threadsafe(self._handle_notification, bytes(data))

    @callback
    def _handle_notification(self, raw: bytes) -> None:
        try:
            parsed = apply_notification(self.state, raw)
        except ProtocolError:
            _LOGGER.debug("Ignoring malformed SoundSticks notification")
            return
        for predicate, future in list(self._waiters):
            if not future.done() and predicate(parsed):
                future.set_result(parsed)
        self.async_set_updated_data(self.state)

    async def _write_wait(self, payload: bytes, predicate: WaitPredicate, wait_seconds: float = 4) -> Frame:
        client = await self._ensure_connected()
        future: asyncio.Future[Frame] = self.hass.loop.create_future()
        waiter = (predicate, future)
        self._waiters.append(waiter)
        try:
            await client.write_gatt_char(COMMAND_UUID, payload, response=False)
            return await asyncio.wait_for(future, wait_seconds)
        finally:
            self._waiters.remove(waiter)

    async def _with_retries(self, operation: Callable[[], Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return await operation()
            except (TimeoutError, OSError, EOFError, BleakError, UpdateFailed) as exc:
                last_error = exc
                self.last_ble_error = type(exc).__name__
                self.ble_status = "retrying"
                await self._disconnect()
                if attempt < 1:
                    await asyncio.sleep(1.5 * (2**attempt))
        assert last_error is not None
        raise last_error

    async def _query_locked(self, payload: bytes, response_command: int) -> Frame:
        return await self._write_wait(payload, lambda item: item.command == response_command)

    async def _refresh_ble_locked(self) -> None:
        for payload, response in (
            (QUERY_LIGHT, 0x32),
            (QUERY_AGGREGATE, 0x42),
            (QUERY_FEEDBACK, 0xF2),
            (QUERY_AUTO_OFF, 0xB9),
            (QUERY_EQ, 0xE2),
        ):
            await self._query_locked(payload, response)

    async def async_refresh_state(self) -> None:
        """Fetch the confirmed state groups requested on App page entry."""
        async with self._io_lock:
            try:
                await self._with_retries(self._refresh_ble_locked)
                self.ble_available = True
            finally:
                self._schedule_disconnect()
        self.async_set_updated_data(self.state)

    async def async_media_command(self, payload: bytes) -> None:
        """Send a media action and read aggregate state back authoritatively."""

        async def command_and_readback() -> None:
            await self._write_wait(
                payload,
                lambda item: item.command == 0x00
                and len(item.data) == 2
                and item.data[0] == 0x43
                and item.data[1] == 0,
            )
            await self._query_locked(QUERY_AGGREGATE, 0x42)

        async with self._io_lock:
            try:
                await self._with_retries(command_and_readback)
                self.ble_available = True
            finally:
                self._schedule_disconnect()
        self.async_set_updated_data(self.state)

    async def async_toggle_playback(self) -> None:
        """Refresh playback state, then perform the App-style single toggle."""

        async def refresh_toggle_readback() -> None:
            await self._query_locked(QUERY_AGGREGATE, 0x42)
            action = "pause" if self.state.playback == 2 else "play"
            await self._write_wait(
                build_media_action(action),
                lambda item: item.command == 0x00
                and len(item.data) == 2
                and item.data[0] == 0x43
                and item.data[1] == 0,
            )
            await self._query_locked(QUERY_AGGREGATE, 0x42)

        async with self._io_lock:
            try:
                await self._with_retries(refresh_toggle_readback)
                self.ble_available = True
            finally:
                self._schedule_disconnect()
        self.async_set_updated_data(self.state)

    async def _async_update_data(self) -> DeviceState:
        async def refresh_ble() -> None:
            async with self._io_lock:
                try:
                    await self._with_retries(self._refresh_ble_locked)
                    self.ble_available = True
                finally:
                    self._schedule_disconnect()

        try:
            await refresh_ble()
        except Exception as exc:
            self.ble_available = False
            self.last_ble_error = type(exc).__name__
            # Discovery and an explicit command can recover later. Do not
            # reject config-entry setup merely because another central owns
            # GATT or a remote proxy is temporarily unavailable at startup.
            _LOGGER.debug("Initial BLE state snapshot failed: %s", type(exc).__name__)

        return self.state

    async def async_command(
        self,
        payload: bytes,
        *,
        ack_command: int | None = None,
        response_command: int | None = None,
        state_update: StateUpdater | None = None,
    ) -> None:
        """Send an allow-listed command and require device confirmation."""
        if ack_command is None and response_command is None:
            raise ValueError("a matching ACK or state response is required")

        def predicate(item: Frame) -> bool:
            if response_command is not None and item.command == response_command:
                return True
            return bool(
                ack_command is not None
                and item.command == 0x00
                and len(item.data) == 2
                and item.data[0] == ack_command
                and item.data[1] == 0
            )

        async with self._io_lock:
            try:
                await self._with_retries(lambda: self._write_wait(payload, predicate))
            finally:
                self._schedule_disconnect()
        if state_update is not None:
            state_update(self.state)
        # Matching notifications have already updated the cache. Avoid the
        # former five-query refresh and its extra reconnect after every write.
        self.async_set_updated_data(self.state)

    async def _write_eq_and_verify_locked(self, steps: tuple[int, ...]) -> None:
        """Write one full EQ snapshot, then verify it with an explicit query."""
        client = await self._ensure_connected()
        await client.write_gatt_char(COMMAND_UUID, build_eq(steps), response=False)

        # Real HK One captures do not show an application ACK for 0xe3.  The
        # query response is the authoritative confirmation instead.
        await self._query_locked(QUERY_EQ, 0xE2)
        actual = self.state.eq_gains_db
        expected = [app_eq_step_to_gain_db(index, step) for index, step in enumerate(steps)]
        if actual is None or len(actual) != 7 or any(abs(left - right) > 0.02 for left, right in zip(actual, expected, strict=True)):
            raise UpdateFailed("EQ readback did not match the requested snapshot")

    async def async_set_eq(self, steps: Sequence[int]) -> None:
        """Set all EQ bands, coalescing superseded slider positions."""
        requested = [round(value) for value in steps]
        # Validate the count and App-scale bounds before changing pending state.
        build_eq(requested)
        self._desired_eq_steps = requested
        self._eq_revision += 1
        revision = self._eq_revision

        # HK One limits drag traffic to roughly one update per 300 ms and
        # always sends the final position.  A short trailing debounce is more
        # suitable for HA service calls over a remote Bluetooth proxy.
        await asyncio.sleep(0.3)
        if revision != self._eq_revision:
            return

        try:
            async with self._io_lock:
                if revision != self._eq_revision:
                    return
                target = tuple(self._desired_eq_steps or requested)
                try:
                    await self._with_retries(lambda: self._write_eq_and_verify_locked(target))
                finally:
                    self._schedule_disconnect()
        except Exception:
            if revision == self._eq_revision:
                self._desired_eq_steps = None
            raise

        if revision == self._eq_revision:
            self._desired_eq_steps = None
            # The e2 response has already populated the authoritative gains.
            self.async_set_updated_data(self.state)

    async def async_set_eq_band(self, index: int, step: int) -> None:
        """Update one App-scale band while preserving the latest pending set."""
        if not 0 <= index < 7:
            raise ValueError("EQ band index is outside 0..6")
        desired = self._desired_eq_steps
        if desired is None:
            gains = self.state.eq_gains_db
            if gains is None:
                raise UpdateFailed("current EQ snapshot is unavailable")
            desired = [gain_db_to_app_eq_step(band, gain) for band, gain in enumerate(gains)]
        else:
            desired = list(desired)
        desired[index] = round(step)
        await self.async_set_eq(desired)

    def _preset_snapshot(self) -> dict[str, Any]:
        """Build a portable preset from fields currently known to HA."""
        state = self.state
        snapshot: dict[str, Any] = {}
        theme = THEME_BY_ID.get(state.theme_id)
        if theme is not None:
            snapshot["theme"] = theme
            color = state.colors.get(state.theme_id)
            if color is not None:
                snapshot["color"] = color
        for key, value in (
            ("light_power", state.light_power),
            ("brightness", state.brightness),
            ("speed", SPEED_BY_ID.get(state.speed)),
            ("volume", state.volume),
            ("feedback_tone", state.feedback_tone),
            ("auto_off", AUTO_OFF_BY_SECONDS.get(state.auto_off_configured)),
        ):
            if value is not None:
                snapshot[key] = value
        if state.eq_gains_db is not None:
            snapshot["eq_steps"] = [
                gain_db_to_app_eq_step(index, gain)
                for index, gain in enumerate(state.eq_gains_db)
            ]
        return snapshot

    async def async_save_preset(self, name: str) -> None:
        """Persist the current confirmed state under a user-selected name."""
        clean_name = " ".join(name.split())
        if not 1 <= len(clean_name) <= 40:
            raise ValueError("preset name must contain 1..40 characters")
        snapshot = self._preset_snapshot()
        if not snapshot:
            raise UpdateFailed("no confirmed device state is available to save")
        presets = dict(self.presets)
        presets[clean_name] = snapshot
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={**self.entry.options, PRESETS_OPTION: presets},
        )
        self.last_applied_preset = clean_name
        self.async_update_listeners()

    async def async_delete_preset(self, name: str) -> None:
        """Delete one persisted preset without touching the speaker."""
        presets = dict(self.presets)
        if name not in presets:
            raise ValueError("unknown preset")
        presets.pop(name)
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={**self.entry.options, PRESETS_OPTION: presets},
        )
        if self.last_applied_preset == name:
            self.last_applied_preset = None
        self.async_update_listeners()

    async def async_apply_preset(self, name: str) -> None:
        """Apply a saved preset through confirmed commands, in a quiet order."""
        preset = self.presets.get(name)
        if not isinstance(preset, dict):
            raise ValueError("unknown preset")

        theme = preset.get("theme")
        color = preset.get("color")
        if theme in THEME_BY_ID.values():
            theme_id = next(key for key, value in THEME_BY_ID.items() if value == theme)
            if isinstance(color, int):
                await self.async_command(
                    build_color(theme_id, color),
                    ack_command=0x33,
                    state_update=lambda state: (
                        setattr(state, "theme_id", theme_id),
                        state.colors.__setitem__(theme_id, color),
                    ),
                )
            else:
                await self.async_command(build_theme(theme), ack_command=0x33)
        if isinstance(preset.get("brightness"), int):
            value = preset["brightness"]
            await self.async_command(
                build_brightness(value),
                ack_command=0x33,
                state_update=lambda state: setattr(state, "brightness", value),
            )
        if preset.get("speed") in SPEED_BY_ID.values():
            value = preset["speed"]
            await self.async_command(
                build_speed(value),
                ack_command=0x33,
                state_update=lambda state: setattr(
                    state,
                    "speed",
                    next(key for key, item in SPEED_BY_ID.items() if item == value),
                ),
            )
        if isinstance(preset.get("volume"), int):
            await self.async_media_command(build_volume(preset["volume"]))
        if isinstance(preset.get("eq_steps"), list):
            await self.async_set_eq(preset["eq_steps"])
        if isinstance(preset.get("feedback_tone"), bool):
            value = preset["feedback_tone"]
            await self.async_command(
                build_feedback_tone(value),
                response_command=0xF2,
                state_update=lambda state: setattr(state, "feedback_tone", value),
            )
        if preset.get("auto_off") in AUTO_OFF_BY_SECONDS.values():
            value = preset["auto_off"]
            await self.async_command(
                build_auto_off(value),
                ack_command=0xBA,
                state_update=lambda state: setattr(
                    state,
                    "auto_off_configured",
                    next(key for key, item in AUTO_OFF_BY_SECONDS.items() if item == value),
                ),
            )
        if isinstance(preset.get("light_power"), bool):
            value = preset["light_power"]
            await self.async_command(
                build_light_power(value),
                ack_command=0x33,
                state_update=lambda state: setattr(state, "light_power", value),
            )
        self.last_applied_preset = name
        self.async_update_listeners()
