"""Config and options flows for SoundSticks 5."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, NAME
from .discovery import matches_soundsticks5_advertisement


class SoundSticks5ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> FlowResult:
        await self.async_set_unique_id("soundsticks5-control-service")
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": discovery_info.name or NAME}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})
        return self.async_show_form(step_id="bluetooth_confirm")

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        candidates = [
            info
            for info in bluetooth.async_discovered_service_info(self.hass, connectable=True)
            if matches_soundsticks5_advertisement(info.name, info.service_uuids, info.service_data)
        ]
        if not candidates:
            return self.async_show_form(step_id="user", errors={"base": "not_found"})
        if user_input is None:
            return self.async_show_form(step_id="user")
        await self.async_set_unique_id("soundsticks5-control-service")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=NAME, data={})
