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
        ble_device=SimpleNamespace(address="rpa"),
        last_update_success=True,
        async_add_listener=lambda _listener, _context=None: lambda: None,
        async_command=AsyncMock(),
        async_set_eq=AsyncMock(),
        async_set_eq_band=AsyncMock(),
        async_media_command=AsyncMock(),
        async_toggle_playback=AsyncMock(),
        async_refresh_state=AsyncMock(),
        async_release_ble=AsyncMock(),
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


async def test_standby_does_not_disable_light_configuration():
    fake = coordinator(DeviceState(light_power=True, auto_off_configured=600, auto_off_remaining=0, playback=1))
    fake.operating_state = "standby"
    entity = SoundSticksLight(fake)
    assert entity.available
    await entity.async_turn_on(brightness=204)
    assert fake.async_command.await_args_list[0].args[0].hex() == "aa330400450150"
    assert fake.async_command.await_args_list[1].args[0].hex() == "aa330400990101"
    # Writing lighting configuration must not invent a physical wake event.
    assert fake.state.auto_off_remaining == 0
    assert fake.state.playback == 1


async def test_dedicated_brightness_uses_app_percent_scale():
    fake = coordinator(DeviceState(light_power=True, brightness=20))
    entity = SoundSticksBrightness(fake)
    await entity.async_set_native_value(73)
    assert fake.async_command.await_args.args[0].hex() == "aa330400450149"


async def test_eq_entity_preserves_other_bands():
    fake = coordinator(DeviceState(eq_gains_db=[0.0] * 7))
    entity = SoundSticksEq(fake, 3, 1000)
    await entity.async_set_native_value(6)
    fake.async_set_eq_band.assert_awaited_once_with(3, 6)


def test_media_player_exposes_ble_state():
    fake = coordinator(DeviceState(playback=1, volume=37))
    entity = SoundSticksMediaPlayer(fake)
    assert entity.available is True
    assert entity.volume_level == 0.37


@pytest.mark.parametrize(
    ("method_name", "expected_frame"),
    [
        ("async_media_pause", "aa430400410101"),
        ("async_media_play", "aa430400410102"),
    ],
)
async def test_media_transport_always_uses_ble_and_updates_state_after_ack(
    method_name: str, expected_frame: str
):
    fake = coordinator(DeviceState(playback=2))
    entity = SoundSticksMediaPlayer(fake)

    await getattr(entity, method_name)()

    assert fake.async_media_command.await_args.args[0].hex() == expected_frame
    assert fake.state.playback == 2


async def test_app_style_play_pause_uses_coordinator_toggle():
    fake = coordinator(DeviceState(playback=2))
    entity = SoundSticksMediaPlayer(fake)
    await entity.async_media_play_pause()
    fake.async_toggle_playback.assert_awaited_once_with()
