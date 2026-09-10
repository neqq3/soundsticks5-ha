from unittest.mock import Mock

import pytest

pytest.importorskip("homeassistant")

from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import async_get_all_descriptions

from custom_components.soundsticks5.services import async_update_preset_choices


async def test_preset_action_choices_refresh_and_allow_new_names_only_when_saving(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    for action in ("save_preset", "apply_preset", "delete_preset"):
        hass.services.async_register("soundsticks5", action, Mock())

    for names in ([], ["夜晚", "Evening"], ["Evening"], []):
        async_update_preset_choices(hass, names)
        descriptions = (await async_get_all_descriptions(hass))["soundsticks5"]
        for action, description in descriptions.items():
            field = description["fields"]["name"]
            selector = field["selector"]["select"]
            assert field["required"] is True
            assert selector["options"] == sorted(names)
            assert selector["mode"] == "dropdown"
            assert selector["custom_value"] is (action == "save_preset")
    await hass.async_block_till_done()


async def test_preset_choices_do_not_register_missing_actions(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    async_update_preset_choices(hass, ["Evening"])
    assert not hass.services.has_service("soundsticks5", "apply_preset")
