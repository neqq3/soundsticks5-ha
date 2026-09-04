"""Async BlueZ D-Bus management using the host bluetoothd instance."""

from __future__ import annotations

import asyncio
from typing import Any

from dbus_next import BusType, Variant
from dbus_next.aio import MessageBus
from dbus_next.errors import DBusError
from dbus_next.service import ServiceInterface, method

BLUEZ = "org.bluez"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
A2DP_SINK_UUID = "0000110b-0000-1000-8000-00805f9b34fb"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
AGENT_IFACE = "org.bluez.Agent1"
AGENT_PATH = "/org/homeassistant/SoundSticks5Agent"
ALLOWED_AUDIO_SERVICES = {
    "00001108-0000-1000-8000-00805f9b34fb",  # Headset
    "0000110a-0000-1000-8000-00805f9b34fb",  # A2DP source
    A2DP_SINK_UUID,
    "0000110c-0000-1000-8000-00805f9b34fb",  # AVRCP target
    "0000110e-0000-1000-8000-00805f9b34fb",  # AVRCP controller
    "00001112-0000-1000-8000-00805f9b34fb",  # Headset audio gateway
    "0000111e-0000-1000-8000-00805f9b34fb",  # Hands-free
}


class BluezUnavailable(RuntimeError):
    pass


class PairingAgent(ServiceInterface):
    """No-input/no-output BlueZ agent, restricted to audio profiles."""

    def __init__(self) -> None:
        super().__init__(AGENT_IFACE)

    @method()
    def Release(self):
        return None

    @method()
    def RequestPinCode(self, device: "o") -> "s":
        del device
        return "0000"

    @method()
    def DisplayPinCode(self, device: "o", pincode: "s"):
        del device, pincode

    @method()
    def RequestPasskey(self, device: "o") -> "u":
        del device
        return 0

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):
        del device, passkey, entered

    @method()
    def RequestConfirmation(self, device: "o", passkey: "u"):
        del device, passkey

    @method()
    def RequestAuthorization(self, device: "o"):
        del device

    @method()
    def AuthorizeService(self, device: "o", uuid: "s"):
        del device
        if uuid.lower() not in ALLOWED_AUDIO_SERVICES:
            raise DBusError("org.bluez.Error.Rejected", "Only audio profiles are authorized")

    @method()
    def Cancel(self):
        return None


def _value(properties: dict[str, Variant], key: str, default: Any = None) -> Any:
    item = properties.get(key)
    return default if item is None else item.value


class BluezManager:
    def __init__(self, adapter_hint: str, device_address: str, alias: str) -> None:
        self.adapter_hint = adapter_hint.lower()
        self.device_address = device_address.upper()
        self.alias = alias.lower()
        self.bus: MessageBus | None = None
        self.agent: PairingAgent | None = None
        self._agent_registered = False

    async def start(self) -> None:
        try:
            self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            await self._objects()
            await self._register_agent()
        except Exception as exc:
            raise BluezUnavailable("host BlueZ D-Bus is unavailable") from exc

    async def _register_agent(self) -> None:
        assert self.bus is not None
        self.agent = PairingAgent()
        self.bus.export(AGENT_PATH, self.agent)
        manager = (await self._proxy("/org/bluez")).get_interface(AGENT_MANAGER_IFACE)
        try:
            await manager.call_register_agent(AGENT_PATH, "NoInputNoOutput")
            self._agent_registered = True
        except DBusError as exc:
            if "AlreadyExists" not in exc.type:
                raise

    async def _proxy(self, path: str):
        if self.bus is None:
            raise BluezUnavailable("BlueZ manager has not started")
        introspection = await self.bus.introspect(BLUEZ, path)
        return self.bus.get_proxy_object(BLUEZ, path, introspection)

    async def _objects(self) -> dict[str, dict[str, dict[str, Variant]]]:
        proxy = await self._proxy("/")
        manager = proxy.get_interface(OBJECT_MANAGER_IFACE)
        return await manager.call_get_managed_objects()

    async def _adapter_path(self) -> str:
        for path, interfaces in (await self._objects()).items():
            props = interfaces.get(ADAPTER_IFACE)
            if props is None:
                continue
            if not self.adapter_hint:
                return path
            address = str(_value(props, "Address", "")).lower()
            alias = str(_value(props, "Alias", "")).lower()
            if self.adapter_hint in {path.rsplit("/", 1)[-1].lower(), address, alias}:
                return path
        raise BluezUnavailable("no matching BlueZ adapter")

    def _matches_device(self, props: dict[str, Variant]) -> bool:
        address = str(_value(props, "Address", "")).upper()
        name = str(_value(props, "Name", "")).lower()
        alias = str(_value(props, "Alias", "")).lower()
        if self.device_address:
            return address == self.device_address
        return self.alias in {name, alias} or "soundsticks 5" in {name, alias}

    @staticmethod
    def _is_soundsticks(props: dict[str, Variant]) -> bool:
        """Reject arbitrary Bluetooth addresses at the pairing boundary."""
        names = {
            str(_value(props, "Name", "")).lower(),
            str(_value(props, "Alias", "")).lower(),
        }
        return any("soundsticks" in name for name in names)

    async def _device(self, *, require: bool = True) -> tuple[str, dict[str, Variant]] | None:
        for path, interfaces in (await self._objects()).items():
            props = interfaces.get(DEVICE_IFACE)
            if props is not None and self._matches_device(props):
                return path, props
        if require:
            raise BluezUnavailable("no cached SoundSticks 5 classic Bluetooth device")
        return None

    async def scan(self, seconds: float = 12) -> list[dict[str, Any]]:
        path = await self._adapter_path()
        adapter = (await self._proxy(path)).get_interface(ADAPTER_IFACE)
        try:
            await adapter.call_set_discovery_filter({"Transport": Variant("s", "auto")})
            await adapter.call_start_discovery()
            await asyncio.sleep(max(1, min(seconds, 30)))
        finally:
            try:
                await adapter.call_stop_discovery()
            except DBusError:
                pass
        devices = []
        for _path, interfaces in (await self._objects()).items():
            props = interfaces.get(DEVICE_IFACE)
            if props is None:
                continue
            name = str(_value(props, "Name", _value(props, "Alias", "")))
            if "soundsticks" not in name.lower():
                continue
            devices.append({
                "name": name,
                "address": str(_value(props, "Address", "")),
                "paired": bool(_value(props, "Paired", False)),
                "connected": bool(_value(props, "Connected", False)),
                "rssi": _value(props, "RSSI"),
            })
        return devices

    async def pair(self, address: str | None = None) -> None:
        if address:
            self.device_address = address.upper()
        item = await self._device(require=False)
        if item is None:
            await self.scan(15)
            item = await self._device()
        assert item is not None
        path, props = item
        if not self._is_soundsticks(props):
            raise BluezUnavailable("refusing to pair a device not identified as SoundSticks")
        proxy = await self._proxy(path)
        device = proxy.get_interface(DEVICE_IFACE)
        if not bool(_value(props, "Paired", False)):
            try:
                await device.call_pair()
            except DBusError as exc:
                if "AlreadyExists" not in exc.type:
                    raise
        await proxy.get_interface(PROPERTIES_IFACE).call_set(DEVICE_IFACE, "Trusted", Variant("b", True))

    async def connect(self) -> None:
        item = await self._device()
        assert item is not None
        path, _props = item
        proxy = await self._proxy(path)
        await proxy.get_interface(PROPERTIES_IFACE).call_set(DEVICE_IFACE, "Trusted", Variant("b", True))
        try:
            await proxy.get_interface(DEVICE_IFACE).call_connect()
        except DBusError as exc:
            if "AlreadyConnected" not in exc.type:
                raise

    async def disconnect(self) -> None:
        item = await self._device(require=False)
        if item is None:
            return
        path, props = item
        if bool(_value(props, "Connected", False)):
            await (await self._proxy(path)).get_interface(DEVICE_IFACE).call_disconnect()

    async def status(self) -> dict[str, Any]:
        item = await self._device(require=False)
        if item is None:
            return {"device_found": False, "paired": False, "audio_connected": False}
        _path, props = item
        uuids = {str(value).lower() for value in _value(props, "UUIDs", [])}
        return {
            "device_found": True,
            "name": str(_value(props, "Alias", _value(props, "Name", "SoundSticks 5"))),
            "address": str(_value(props, "Address", "")),
            "paired": bool(_value(props, "Paired", False)),
            "trusted": bool(_value(props, "Trusted", False)),
            "audio_connected": bool(_value(props, "Connected", False)),
            "a2dp_sink": A2DP_SINK_UUID in uuids,
        }

    async def stop(self) -> None:
        if self.bus is None:
            return
        if self._agent_registered:
            try:
                manager = (await self._proxy("/org/bluez")).get_interface(AGENT_MANAGER_IFACE)
                await manager.call_unregister_agent(AGENT_PATH)
            except DBusError:
                pass
        if self.agent is not None:
            self.bus.unexport(AGENT_PATH, AGENT_IFACE)
        self.bus.disconnect()
        self.bus = None
        self.agent = None
        self._agent_registered = False
