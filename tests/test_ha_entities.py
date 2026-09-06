from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("homeassistant")

from custom_components.soundsticks5.light import SoundSticksLight
from custom_components.soundsticks5.media_player import SoundSticksMediaPlayer
from custom_components.soundsticks5.number import SoundSticksBrightness, SoundSticksEq
from custom_components.soundsticks5.protocol import DeviceState


def coordinator(state: DeviceState):
    return SimpleNamespace(
        state=state,
        data=state,
        ble_available=True,
        backend_enabled=False,
        backend_status={"available": False},
        last_update_success=True,
        async_add_listener=lambda _listener, _context=None: lambda: None,
        async_command=AsyncMock(),
        async_backend_action=AsyncMock(),
        entry=SimpleNamespace(options={}),
    )


async def test_light_uses_two_confirmed_commands_when_brightness_and_power_change():
    fake = coordinator(DeviceState(light_power=False, brightness=20))
    entity = SoundSticksLight(fake)
    await entity.async_turn_on(brightness=128)
    assert fake.async_command.await_count == 2
    assert fake.async_command.await_args_list[0].args[0].hex() == "aa330400450132"
    assert fake.async_command.await_args_list[1].args[0].hex() == "aa330400990101"


async def test_light_always_sends_on_even_when_cached_state_is_stale():
    fake = coordinator(DeviceState(light_power=True, brightness=20))
    entity = SoundSticksLight(fake)
    await entity.async_turn_on()
    assert fake.async_command.await_count == 1
    assert fake.async_command.await_args.args[0].hex() == "aa330400990101"


async def test_dedicated_brightness_uses_app_percent_scale():
    fake = coordinator(DeviceState(light_power=True, brightness=20))
    entity = SoundSticksBrightness(fake)
    await entity.async_set_native_value(73)
    assert fake.async_command.await_args.args[0].hex() == "aa330400450149"


async def test_eq_entity_preserves_other_bands():
    fake = coordinator(DeviceState(eq_gains_db=[0.0] * 7))
    entity = SoundSticksEq(fake, 3, 1000)
    await entity.async_set_native_value(6)
    frame = fake.async_command.await_args.args[0]
    assert frame[:4].hex() == "aae36100"


def test_media_player_survives_missing_optional_backend():
    fake = coordinator(DeviceState(playback=1, volume=37))
    entity = SoundSticksMediaPlayer(fake)
    assert entity.available is True
    assert entity.volume_level == 0.37
