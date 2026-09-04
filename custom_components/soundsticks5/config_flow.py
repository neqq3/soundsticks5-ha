"""Config and options flows for SoundSticks 5."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_CONNECT,
    CONF_AUTO_RECONNECT,
    CONF_AUTO_RELEASE,
    CONF_BACKEND_TOKEN,
    CONF_BACKEND_URL,
    CONF_ENABLE_AUDIO,
    CONF_KEEP_BLE_CONNECTED,
    CONF_RELEASE_DELAY,
    CONF_WAKE_BEHAVIOR,
    CONTROL_SERVICE_UUID,
    DEFAULT_BACKEND_URL,
    DEFAULT_RELEASE_DELAY,
    DEFAULT_WAKE_BEHAVIOR,
    DOMAIN,
    NAME,
    WAKE_BEHAVIORS,
)


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
            if CONTROL_SERVICE_UUID in {uuid.lower() for uuid in info.service_uuids}
        ]
        if not candidates:
            return self.async_show_form(step_id="user", errors={"base": "not_found"})
        if user_input is None:
            return self.async_show_form(step_id="user")
        await self.async_set_unique_id("soundsticks5-control-service")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=NAME, data={})

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return SoundSticks5OptionsFlow()


class SoundSticks5OptionsFlow(config_entries.OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(CONF_ENABLE_AUDIO, default=current.get(CONF_ENABLE_AUDIO, True)): bool,
                vol.Required(CONF_BACKEND_URL, default=current.get(CONF_BACKEND_URL, DEFAULT_BACKEND_URL)): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
                vol.Optional(CONF_BACKEND_TOKEN, default=current.get(CONF_BACKEND_TOKEN, "")): str,
                vol.Required(CONF_WAKE_BEHAVIOR, default=current.get(CONF_WAKE_BEHAVIOR, DEFAULT_WAKE_BEHAVIOR)): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(WAKE_BEHAVIORS),
                        translation_key="wake_behavior",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_RELEASE_DELAY, default=current.get(CONF_RELEASE_DELAY, DEFAULT_RELEASE_DELAY)): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
                vol.Required(CONF_AUTO_RELEASE, default=current.get(CONF_AUTO_RELEASE, True)): bool,
                vol.Required(CONF_AUTO_CONNECT, default=current.get(CONF_AUTO_CONNECT, False)): bool,
                vol.Required(CONF_AUTO_RECONNECT, default=current.get(CONF_AUTO_RECONNECT, True)): bool,
                vol.Required(CONF_KEEP_BLE_CONNECTED, default=current.get(CONF_KEEP_BLE_CONNECTED, False)): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
