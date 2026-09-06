"""Constants for the SoundSticks 5 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "soundsticks5"
NAME: Final = "SoundSticks 5"
VERSION: Final = "1.2.0"
CONTROL_SERVICE_UUID: Final = "65786365-6c70-6f69-6e74-2e636f6d0000"
NOTIFY_UUID: Final = "65786365-6c70-6f69-6e74-2e636f6d0001"
COMMAND_UUID: Final = "65786365-6c70-6f69-6e74-2e636f6d0002"
HARMAN_DISCOVERY_UUID: Final = "0000fddf-0000-1000-8000-00805f9b34fb"
FAST_PAIR_UUID: Final = "0000fe2c-0000-1000-8000-00805f9b34fb"
PLATFORMS: Final = ["button", "light", "media_player", "number", "select", "sensor", "switch"]
THEMES: Final = {"ocean": (0x10, 54), "aurora": (0x11, 50), "blossom": (0x12, 75), "sunrise": (0x13, 60), "fireplace": (0x14, 72), "static": (0x15, 0)}
THEME_BY_ID: Final = {value[0]: key for key, value in THEMES.items()}
SPEEDS: Final = {"low": 1, "medium": 2, "high": 3}
SPEED_BY_ID: Final = {value: key for key, value in SPEEDS.items()}
AUTO_OFF_SECONDS: Final = {"never": 0, "10_minutes": 600, "1_hour": 3600, "2_hours": 7200, "4_hours": 14400}
AUTO_OFF_BY_SECONDS: Final = {value: key for key, value in AUTO_OFF_SECONDS.items()}
EQ_FREQUENCIES: Final = (125, 250, 500, 1000, 2000, 4000, 8000)
BLE_IDLE_DISCONNECT_SECONDS: Final = 10
PRESETS_OPTION: Final = "presets"
QUERY_LIGHT: Final = bytes.fromhex("aa 31 00")
QUERY_AGGREGATE: Final = bytes.fromhex("aa 41 00")
QUERY_EQ: Final = bytes.fromhex("aa e1 00")
QUERY_FEEDBACK: Final = bytes.fromhex("aa f1 00")
QUERY_AUTO_OFF: Final = bytes.fromhex("aa b8 00")
