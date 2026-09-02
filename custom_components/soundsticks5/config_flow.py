"""Config flow for SoundSticks 5."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .const import CONTROL_SERVICE_UUID, DOMAIN, NAME


class SoundSticks5ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one SoundSticks 5 integration entry."""

    VERSION = 1

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        await self.async_set_unique_id("soundsticks5-control-service")
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": discovery_info.name or NAME}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})
        return self.async_show_form(step_id="bluetooth_confirm")

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        candidates = [
            info
            for info in bluetooth.async_discovered_service_info(self.hass, connectable=True)
            if CONTROL_SERVICE_UUID in {uuid.lower() for uuid in info.service_uuids}
        ]
        if not candidates:
            return self.async_abort(reason="not_found")
        await self.async_set_unique_id("soundsticks5-control-service")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=NAME, data={})
