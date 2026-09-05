from custom_components.soundsticks5.const import (
    CONTROL_SERVICE_UUID,
    FAST_PAIR_UUID,
    HARMAN_DISCOVERY_UUID,
)
from custom_components.soundsticks5.discovery import matches_soundsticks5_advertisement


def test_matches_current_awake_advertisement():
    assert matches_soundsticks5_advertisement(
        "SoundSticks 5",
        [HARMAN_DISCOVERY_UUID, FAST_PAIR_UUID],
        {FAST_PAIR_UUID: bytes.fromhex("08 a0 d5")},
    )


def test_matches_private_control_service_advertisement():
    assert matches_soundsticks5_advertisement(None, [CONTROL_SERVICE_UUID], {})


def test_matches_observed_anonymous_standby_marker():
    assert matches_soundsticks5_advertisement(None, [FAST_PAIR_UUID], {FAST_PAIR_UUID: b"\x00\x00"})


def test_rejects_other_harman_and_fast_pair_devices():
    assert not matches_soundsticks5_advertisement("Other Harman Speaker", [HARMAN_DISCOVERY_UUID], {})
    assert not matches_soundsticks5_advertisement(
        None,
        [FAST_PAIR_UUID],
        {FAST_PAIR_UUID: bytes.fromhex("08 a0 d5")},
    )
