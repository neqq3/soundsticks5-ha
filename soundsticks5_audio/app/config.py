"""App configuration loaded from Home Assistant's options file."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    adapter: str = ""
    device_address: str = ""
    device_alias: str = "SoundSticks 5"
    api_token: str = ""
    auto_connect: bool = False
    auto_reconnect: bool = True
    release_after_playback: bool = True
    release_delay: int = 3
    max_playback_seconds: int = 21600
    sink_match: str = "bluez_output"
    port: int = 8099


def load_config(path: str | Path | None = None) -> AppConfig:
    source = Path(path or os.environ.get("SS5_OPTIONS", "/data/options.json"))
    values = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {}
    return AppConfig(
        adapter=str(values.get("adapter", "")),
        device_address=str(values.get("device_address", "")).upper(),
        device_alias=str(values.get("device_alias", "SoundSticks 5")),
        api_token=str(values.get("api_token", "")),
        auto_connect=bool(values.get("auto_connect", False)),
        auto_reconnect=bool(values.get("auto_reconnect", True)),
        release_after_playback=bool(values.get("release_after_playback", True)),
        release_delay=max(0, min(60, int(values.get("release_delay", 3)))),
        max_playback_seconds=max(1, min(86400, int(values.get("max_playback_seconds", 21600)))),
        sink_match=str(values.get("sink_match", "bluez_output")),
        port=int(os.environ.get("SS5_PORT", "8099")),
    )
