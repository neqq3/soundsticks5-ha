"""BLE and optional audio-backend coordinator for SoundSticks 5."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothChange, BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .backend import AudioBackendClient, BackendUnavailable
from .const import (
    COMMAND_UUID,
    CONF_AUTO_CONNECT,
    CONF_BACKEND_TOKEN,
    CONF_BACKEND_URL,
    CONF_ENABLE_AUDIO,
    CONF_KEEP_BLE_CONNECTED,
    CONTROL_SERVICE_UUID,
    DEFAULT_BACKEND_URL,
    FAST_PAIR_UUID,
    HARMAN_DISCOVERY_UUID,
    NAME,
    NOTIFY_UUID,
    QUERY_AGGREGATE,
    QUERY_AUTO_OFF,
    QUERY_EQ,
    QUERY_FEEDBACK,
    QUERY_LIGHT,
)
from .discovery import matches_soundsticks5_advertisement
from .protocol import DeviceState, Frame, ProtocolError, apply_notification

_LOGGER = logging.getLogger(__name__)
WaitPredicate = Callable[[Frame], bool]


class SoundSticksCoordinator(DataUpdateCoordinator[DeviceState]):
    """Own serialized GATT I/O and merge optional audio backend state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=NAME, update_interval=timedelta(seconds=30))
        self.entry = entry
        self.state = DeviceState()
        self.ble_device: BLEDevice | None = None
        self.ble_available = False
        self.ble_status = "not_seen"
        self.last_ble_error: str | None = None
        self.rssi: int | None = None
        self._client: BleakClient | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._backend_task: asyncio.Task[None] | None = None
        self._io_lock = asyncio.Lock()
        self._waiters: list[tuple[WaitPredicate, asyncio.Future[Frame]]] = []
        self.backend_status: dict[str, Any] = {"available": False, "audio_connected": False, "playing": False}
        options = entry.options
        self.backend_enabled = options.get(CONF_ENABLE_AUDIO, True)
        self._auto_connect_pending = bool(options.get(CONF_AUTO_CONNECT, False))
        self.backend = AudioBackendClient(
            hass,
            options.get(CONF_BACKEND_URL, DEFAULT_BACKEND_URL),
            options.get(CONF_BACKEND_TOKEN, ""),
        )

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
        if self.backend_enabled:
            self._backend_task = self.hass.async_create_task(
                self.backend.listen(self._backend_event),
                "soundsticks5 audio backend events",
            )

    async def _backend_event(self, event: dict[str, Any]) -> None:
        """Merge a websocket event and fetch a full state after transitions."""
        if event.get("event") == "status":
            self.backend_status = {"available": True, **event}
        else:
            try:
                self.backend_status = {"available": True, **await self.backend.status()}
            except BackendUnavailable:
                self.backend_status = {"available": False, "audio_connected": False, "playing": False}
        self.async_update_listeners()

    def _matches_advertisement(self, info: BluetoothServiceInfoBleak) -> bool:
        return matches_soundsticks5_advertisement(info.name, info.service_uuids, info.service_data)

    @callback
    def _remember(self, info: BluetoothServiceInfoBleak) -> None:
        self.ble_device = info.device
        self.rssi = info.rssi
        self.ble_available = True
        if self.ble_status == "not_seen":
            self.ble_status = "advertising"

    async def async_stop(self) -> None:
        for unsubscribe in self._unsubs:
            unsubscribe()
        self._unsubs.clear()
        if self._backend_task is not None:
            self._backend_task.cancel()
            await asyncio.gather(self._backend_task, return_exceptions=True)
            self._backend_task = None
        async with self._io_lock:
            await self._disconnect()

    async def _disconnect(self) -> None:
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            try:
                await client.disconnect()
            except Exception as exc:  # pragma: no cover - adapter dependent
                _LOGGER.debug("BLE disconnect failed: %s", type(exc).__name__)
        self.ble_status = "advertising" if self.ble_device else "not_seen"

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

    async def _ensure_connected(self) -> BleakClient:
        if self.ble_device is None:
            raise UpdateFailed("speaker has not been seen by Home Assistant Bluetooth")
        if self._client is not None and self._client.is_connected:
            if self._client.address == self.ble_device.address:
                return self._client
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
        for attempt in range(3):
            try:
                return await operation()
            except (TimeoutError, OSError, EOFError, BleakError, UpdateFailed) as exc:
                last_error = exc
                self.last_ble_error = type(exc).__name__
                self.ble_status = "retrying"
                await self._disconnect()
                if attempt < 2:
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

    async def _async_update_data(self) -> DeviceState:
        async def refresh_ble() -> None:
            async with self._io_lock:
                try:
                    await self._with_retries(self._refresh_ble_locked)
                    self.ble_available = True
                finally:
                    if not self.entry.options.get(CONF_KEEP_BLE_CONNECTED, False):
                        await self._disconnect()

        try:
            await refresh_ble()
        except Exception as exc:
            self.ble_available = False
            self.last_ble_error = type(exc).__name__
            if not self.backend_enabled:
                raise UpdateFailed("BLE state refresh failed") from exc

        if self.backend_enabled:
            try:
                status = await self.backend.status()
                self.backend_status = {"available": True, **status}
                if self._auto_connect_pending:
                    self._auto_connect_pending = False
                    if status.get("paired") and not status.get("audio_connected"):
                        self.backend_status = {"available": True, **await self.backend.action("connect")}
            except BackendUnavailable:
                self.backend_status = {"available": False, "audio_connected": False, "playing": False}
        return self.state

    async def async_command(
        self,
        payload: bytes,
        *,
        ack_command: int | None = None,
        response_command: int | None = None,
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
                if not self.entry.options.get(CONF_KEEP_BLE_CONNECTED, False):
                    await self._disconnect()
        await self.async_request_refresh()

    async def async_backend_action(self, action: str, **payload: Any) -> dict[str, Any]:
        if not self.backend_enabled:
            raise BackendUnavailable("audio backend is disabled")
        result = await self.backend.action(action, **payload)
        try:
            self.backend_status = {"available": True, **await self.backend.status()}
        except BackendUnavailable:
            pass
        self.async_update_listeners()
        return result
