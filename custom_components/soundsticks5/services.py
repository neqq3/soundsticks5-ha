"""Dynamic preset choices for the action editor."""

from collections.abc import Iterable

from homeassistant.const import EVENT_SERVICE_REGISTERED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.service import async_set_service_schema

from .const import DOMAIN


@callback
def async_update_preset_choices(hass: HomeAssistant, names: Iterable[str]) -> None:
    """Refresh action choices without changing service IDs or stored automations."""
    options = sorted(names)
    for action in ("save_preset", "apply_preset", "delete_preset"):
        if not hass.services.has_service(DOMAIN, action):
            continue
        async_set_service_schema(
            hass,
            DOMAIN,
            action,
            {
                "fields": {
                    "name": {
                        "required": True,
                        "selector": {
                            "select": {
                                "options": options,
                                "mode": "dropdown",
                                "custom_value": action == "save_preset",
                            }
                        },
                    }
                }
            },
        )
        # Connected frontends invalidate their cached action descriptions on this event.
        hass.bus.async_fire(EVENT_SERVICE_REGISTERED, {"domain": DOMAIN, "service": action})
