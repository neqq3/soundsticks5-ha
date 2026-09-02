"""Constants for the SoundSticks 5 integration."""

DOMAIN = "soundsticks5"
NAME = "SoundSticks 5"

CONTROL_SERVICE_UUID = "65786365-6c70-6f69-6e74-2e636f6d0000"
NOTIFY_UUID = "65786365-6c70-6f69-6e74-2e636f6d0001"
COMMAND_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"

QUERY_LIGHT = bytes.fromhex("aa 31 00")

THEMES = {
    "ocean": (0x10, 54),
    "aurora": (0x11, 50),
    "blossom": (0x12, 75),
    "sunrise": (0x13, 60),
    "fireplace": (0x14, 72),
    "static": (0x15, 0),
}
THEME_BY_ID = {value[0]: key for key, value in THEMES.items()}

SPEEDS = {"low": 1, "medium": 2, "high": 3}
SPEED_BY_ID = {value: key for key, value in SPEEDS.items()}

PLATFORMS = ["light", "select", "number"]
