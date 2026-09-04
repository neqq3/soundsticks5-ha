from pathlib import Path

import pytest

from soundsticks5_audio.app.audio import AudioPlayer
from soundsticks5_audio.app.config import load_config


def test_url_sources_are_allowed():
    assert AudioPlayer.validate_source("https://example.invalid/tts.mp3") == "https://example.invalid/tts.mp3"


def test_non_media_local_path_is_rejected():
    with pytest.raises(ValueError):
        AudioPlayer.validate_source(str(Path.cwd() / "private.mp3"))


def test_options_are_clamped(tmp_path, monkeypatch):
    options = tmp_path / "options.json"
    options.write_text('{"release_delay": 999, "device_address": "aa:bb:cc:dd:ee:ff"}', encoding="utf-8")
    monkeypatch.setenv("SS5_PORT", "8123")
    config = load_config(options)
    assert config.release_delay == 60
    assert config.device_address == "AA:BB:CC:DD:EE:FF"
    assert config.port == 8123

