"""Bluetooth coordinator for SoundSticks 5."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothChange, BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import COMMAND_UUID, CONTROL_SERVICE_UUID, NOTIFY_UUID, QUERY_LIGHT
from .protocol import LightState, ProtocolError, parse_light_state

_LOGGER = logging.getLogger(__name__)


class SoundSticksCoordinator(DataUpdateCoordinator[LightState]):
    """Keep the freshest BLEDevice while using short-lived GATT sessions."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="SoundSticks 5",
            update_interval=timedelta(seconds=30),
        )
        self.ble_device: BLEDevice | None = None
        self._unsub = None
        self._io_lock = asyncio.Lock()

    async def async_start(self) -> None:
        """Start listening for current advertisements."""
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            if CONTROL_SERVICE_UUID in {u.lower() for u in info.service_uuids}:
                self.ble_device = info.device
                break

        @callback
        def _on_bluetooth(
            info: BluetoothServiceInfoBleak, change: BluetoothChange
        ) -> None:
            self.ble_device = info.device

        self._unsub = bluetooth.async_register_callback(
            self.hass,
            _on_bluetooth,
            {"service_uuid": CONTROL_SERVICE_UUID},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )

    async def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def _async_connect(self) -> BleakClient:
        if self.ble_device is None:
            raise UpdateFailed("SoundSticks 5 has not been seen by Home Assistant Bluetooth")
        client = BleakClient(self.ble_device, timeout=15.0)
        await client.connect()
        service_uuids = {str(service.uuid).lower() for service in client.services}
        if CONTROL_SERVICE_UUID not in service_uuids:
            await client.disconnect()
            raise UpdateFailed("Connected device does not expose the SoundSticks 5 control service")
        return client

    async def _async_update_data(self) -> LightState:
        try:
            return await self.async_query_light()
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc

    async def async_query_light(self) -> LightState:
        async with self._io_lock:
            client = await self._async_connect()
            response = asyncio.get_running_loop().create_future()

            def _notify(_sender, data: bytearray) -> None:
                if response.done():
                    return
                raw = bytes(data)
                if len(raw) >= 2 and raw[0] == 0xAA and raw[1] == 0x32:
                    response.set_result(raw)

            try:
                await client.start_notify(NOTIFY_UUID, _notify)
                await client.write_gatt_char(COMMAND_UUID, QUERY_LIGHT, response=False)
                raw = await asyncio.wait_for(response, timeout=3.0)
                return parse_light_state(raw)
            finally:
                try:
                    await client.stop_notify(NOTIFY_UUID)
                except Exception:
                    pass
                await client.disconnect()

    async def async_send(self, payload: bytes) -> None:
        """Send one confirmed setting frame and release the GATT connection."""
        async with self._io_lock:
            client = await self._async_connect()
            try:
                await client.write_gatt_char(COMMAND_UUID, payload, response=False)
                await asyncio.sleep(0.15)
            finally:
                await client.disconnect()
        await self.async_request_refresh()
