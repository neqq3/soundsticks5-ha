from dbus_next import Variant

from soundsticks5_audio.app.bluez import BluezManager


def test_pairing_identity_guard_accepts_soundsticks_name():
    properties = {
        "Address": Variant("s", "00:11:22:33:44:55"),
        "Name": Variant("s", "SoundSticks 5"),
    }
    assert BluezManager._is_soundsticks(properties)


def test_pairing_identity_guard_rejects_unrelated_address():
    properties = {
        "Address": Variant("s", "00:11:22:33:44:55"),
        "Alias": Variant("s", "Nearby headphones"),
    }
    assert not BluezManager._is_soundsticks(properties)
