import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_manifest_and_translations_are_valid():
    manifest = json.loads((ROOT / "custom_components/soundsticks5/manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "soundsticks5"
    assert manifest["config_flow"] is True
    assert manifest["bluetooth"][0]["service_uuid"].endswith("0000")
    assert manifest["bluetooth"][1] == {
        "service_uuid": "0000fddf-0000-1000-8000-00805f9b34fb",
        "local_name": "SoundSticks 5*",
        "connectable": True,
    }
    for path in (ROOT / "custom_components/soundsticks5").glob("**/*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_app_configuration_and_build_matrix():
    app = yaml.safe_load((ROOT / "soundsticks5_audio/config.yaml").read_text(encoding="utf-8"))
    build = yaml.safe_load((ROOT / "soundsticks5_audio/build.yaml").read_text(encoding="utf-8"))
    assert app["host_dbus"] is True
    assert app["audio"] is True
    assert set(app["arch"]) == set(build["build_from"])


def test_high_risk_protocols_are_not_exposed():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "custom_components/soundsticks5").glob("*.py")
    ).lower()
    assert "arbitrary_write" not in source
    assert "factory_reset" not in source
    assert "firmware_update" not in source


def test_default_app_url_targets_haos_host_not_core_loopback():
    source = (ROOT / "custom_components/soundsticks5/const.py").read_text(encoding="utf-8")
    assert 'DEFAULT_BACKEND_URL: Final = "http://172.30.32.1:8099"' in source


def test_ble_coordinator_has_no_periodic_poll_or_post_command_refresh():
    source = (ROOT / "custom_components/soundsticks5/coordinator.py").read_text(encoding="utf-8")
    assert "update_interval=None" in source
    assert "timedelta(seconds=30)" not in source
    assert "await self.async_request_refresh()" not in source
