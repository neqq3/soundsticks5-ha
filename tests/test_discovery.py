from .load_protocol import load_module

discovery = load_module("discovery")
CONTROL_SERVICE_UUID = discovery.CONTROL_SERVICE_UUID
FAST_PAIR_UUID = discovery.FAST_PAIR_UUID
HARMAN_DISCOVERY_UUID = discovery.HARMAN_DISCOVERY_UUID
matches_soundsticks5_advertisement = discovery.matches_soundsticks5_advertisement


def test_matches_current_awake_advertisement():
    assert matches_soundsticks5_advertisement(
        "SoundSticks 5",
        [HARMAN_DISCOVERY_UUID, FAST_PAIR_UUID],
        {FAST_PAIR_UUID: bytes.fromhex("08 a0 d5")},
    )


def test_matches_private_control_service_advertisement():
    assert matches_soundsticks5_advertisement(None, [CONTROL_SERVICE_UUID], {})


def test_matches_named_service_data_only_advertisement():
    # Orange Pi / BlueZ observation: FDDF and FE2C data, empty UUID list.
    # Payload identity bytes are omitted; matching does not interpret them.
    assert matches_soundsticks5_advertisement(
        "SoundSticks 5", [],
        {HARMAN_DISCOVERY_UUID: b"\x31\x21", FAST_PAIR_UUID: b"\x00\x00"},
    )
    # FDDF callback must also work without an unrelated Fast Pair field.
    assert matches_soundsticks5_advertisement(
        "SoundSticks 5", [], {HARMAN_DISCOVERY_UUID.upper(): b"\x31\x21"},
    )
    assert not matches_soundsticks5_advertisement(
        "Other Harman Speaker", [], {HARMAN_DISCOVERY_UUID: b"\x31\x21"},
    )
    assert not matches_soundsticks5_advertisement("SoundSticks 5", [], {})


def test_matches_observed_anonymous_standby_marker():
    assert matches_soundsticks5_advertisement(None, [FAST_PAIR_UUID], {FAST_PAIR_UUID: b"\x00\x00"})
    assert matches_soundsticks5_advertisement(
        "00:11:22:33:44:55",
        [FAST_PAIR_UUID],
        {FAST_PAIR_UUID: b"\x00\x00"},
    )


def test_rejects_other_harman_and_fast_pair_devices():
    assert not matches_soundsticks5_advertisement("Other Harman Speaker", [HARMAN_DISCOVERY_UUID], {})
    assert not matches_soundsticks5_advertisement(
        None,
        [FAST_PAIR_UUID],
        {FAST_PAIR_UUID: bytes.fromhex("08 a0 d5")},
    )
    assert not matches_soundsticks5_advertisement(
        "Named Fast Pair device",
        [FAST_PAIR_UUID],
        {FAST_PAIR_UUID: b"\x00\x00"},
    )
