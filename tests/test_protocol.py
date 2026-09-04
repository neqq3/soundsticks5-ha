import math

import pytest

from .load_protocol import load_protocol

p = load_protocol()


@pytest.mark.parametrize(
    ("factory", "argument", "expected"),
    [
        (p.build_light_power, True, "aa330400990101"),
        (p.build_brightness, 100, "aa330400450164"),
        (p.build_speed, "medium", "aa3304004d0102"),
        (p.build_theme, "ocean", "aa3308004f01104c021036"),
        (p.build_media_action, "pause", "aa430400410101"),
        (p.build_media_action, "play", "aa430400410102"),
        (p.build_media_action, "previous", "aa430400410103"),
        (p.build_media_action, "next", "aa430400410104"),
        (p.build_volume, 37, "aa430400420125"),
        (p.build_feedback_tone, False, "aaf30100"),
        (p.build_auto_off, "10_minutes", "aaba025802"),
    ],
)
def test_confirmed_frames(factory, argument, expected):
    assert factory(argument).hex() == expected


def test_light_state_notification():
    state = p.DeviceState()
    p.apply_notification(state, bytes.fromhex("aa 32 0a 00 99 01 01 45 01 64 4d 01 02"))
    assert state.light_power is True
    assert state.brightness == 100
    assert state.speed == 2


def test_aggregate_state_and_unknown_36_stays_raw():
    state = p.DeviceState()
    raw = bytes.fromhex("aa 42 11 00 41 01 02 42 01 25 44 02 4869 45 01 41 36 01 07")
    p.apply_notification(state, raw)
    assert state.playback == 2
    assert state.volume == 37
    assert state.track_title == "Hi"
    assert state.artist == "A"
    assert state.unknown_36 == 7


def test_feedback_and_auto_off_state():
    state = p.DeviceState()
    p.apply_notification(state, bytes.fromhex("aa f2 01 01"))
    p.apply_notification(state, bytes.fromhex("aa b9 04 58 02 55 02"))
    assert state.feedback_tone is True
    assert state.auto_off_configured == 600
    assert state.auto_off_remaining == 597


def test_eq_layout_and_round_trip():
    steps = [-12, -8, -4, 0, 4, 8, 12]
    command = p.build_eq(steps)
    assert command[:4] == bytes.fromhex("aa e3 61 00")
    assert len(command) == 101
    response = bytes((0xAA, 0xE2, 97, 0)) + command[4:]
    state = p.DeviceState()
    p.apply_notification(state, response)
    assert state.eq_gains_db is not None
    assert [p.gain_db_to_app_eq_step(i, value) for i, value in enumerate(state.eq_gains_db)] == steps
    assert math.isclose(state.eq_gains_db[0], -9.0)


def test_eq_reset_is_full_seven_filter_snapshot():
    command = p.build_eq_reset()
    assert command[:4] == bytes.fromhex("aa e3 61 00")
    assert len(command) == 101


@pytest.mark.parametrize("value", [-1, 101])
def test_percent_rejects_out_of_range(value):
    with pytest.raises(p.ProtocolError):
        p.build_volume(value)


def test_malformed_frame_is_rejected():
    with pytest.raises(p.ProtocolError):
        p.decode_frame(bytes.fromhex("aa 42 02 00"))
