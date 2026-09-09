"""Resource installation contracts, runnable without a Bluetooth host."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

ROOT = Path(__file__).parents[1]


@pytest.fixture
def frontend(monkeypatch):
    # Load this module alone on Windows; CI uses real Home Assistant classes.
    if importlib.util.find_spec("homeassistant") is None:
        for name in (
            "homeassistant.components.http",
            "homeassistant.components.lovelace.resources",
            "homeassistant.core",
        ):
            module = ModuleType(name)
            monkeypatch.setitem(sys.modules, name, module)
        sys.modules["homeassistant.components.http"].StaticPathConfig = lambda *args: args
        sys.modules["homeassistant.components.lovelace.resources"].ResourceStorageCollection = type("Storage", (), {})
        sys.modules["homeassistant.core"].HomeAssistant = object
    spec = importlib.util.spec_from_file_location(
        "ss5_frontend_test", ROOT / "custom_components/soundsticks5/frontend.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def storage(frontend, items):
    result = Mock(spec=frontend.ResourceStorageCollection)
    result.async_get_info = AsyncMock()
    result.async_items = Mock(return_value=items)

    async def create(data):
        items.append({"id": "new", "url": data["url"], "type": data["res_type"]})

    async def update(item_id, data):
        next(item for item in items if item["id"] == item_id).update(url=data["url"], type=data["res_type"])

    async def delete(item_id):
        items[:] = [item for item in items if item["id"] != item_id]

    result.async_create_item = AsyncMock(side_effect=create)
    result.async_update_item = AsyncMock(side_effect=update)
    result.async_delete_item = AsyncMock(side_effect=delete)
    return result


async def test_fresh_install_and_repeat_do_not_duplicate(frontend):
    items = []
    resources = storage(frontend, items)
    url = frontend.CARD_URL + "?v=one"
    await frontend.async_register_resource(resources, url)
    await frontend.async_register_resource(resources, url)
    resources.async_create_item.assert_awaited_once()
    resources.async_update_item.assert_not_awaited()
    assert items == [{"id": "new", "url": url, "type": "module"}]


async def test_upgrade_migrates_legacy_and_preserves_other_cards(frontend):
    untouched = [
        {"id": "other", "url": "/local/other.js", "type": "module"},
        {"id": "similar", "url": frontend.LEGACY_URL + ".backup", "type": "module"},
        {"id": "remote", "url": "https://example.com" + frontend.LEGACY_URL, "type": "module"},
    ]
    items = [
        {"id": "old", "url": frontend.LEGACY_URL + "?v=old", "type": "js"},
        {"id": "duplicate", "url": frontend.CARD_URL + "?v=old", "type": "module"},
        *untouched,
    ]
    resources = storage(frontend, items)
    url = frontend.CARD_URL + "?v=new"
    await frontend.async_register_resource(resources, url)
    assert items == [{"id": "old", "url": url, "type": "module"}, *untouched]


async def test_yaml_is_not_mutated(frontend):
    resources = SimpleNamespace(data=[{"url": frontend.LEGACY_URL, "type": "module"}])
    await frontend.async_register_resource(resources, frontend.CARD_URL)
    assert resources.data == [{"url": frontend.LEGACY_URL, "type": "module"}]


async def test_setup_serves_assets_even_if_resource_storage_fails(frontend):
    resources = storage(frontend, [])
    resources.async_get_info.side_effect = OSError("storage unavailable")
    hass = SimpleNamespace(
        data={"lovelace": SimpleNamespace(resources=resources)},
        http=SimpleNamespace(async_register_static_paths=AsyncMock()),
        async_add_executor_job=AsyncMock(side_effect=lambda job: job()),
    )
    await frontend.async_setup_frontend(hass)
    hass.http.async_register_static_paths.assert_awaited_once()


def test_both_assets_change_resource_version(frontend, tmp_path, monkeypatch):
    monkeypatch.setattr(frontend, "FRONTEND_DIR", tmp_path)
    js = tmp_path / "soundsticks5-lovelace.js"
    image = tmp_path / "soundsticks5.png"
    js.write_bytes(b"script")
    image.write_bytes(b"image")
    first = frontend._asset_version()
    image.write_bytes(b"new image")
    second = frontend._asset_version()
    js.write_bytes(b"new script")
    assert len({first, second, frontend._asset_version()}) == 3


def test_hacs_package_contains_runtime_assets(frontend):
    assert (frontend.FRONTEND_DIR / "soundsticks5.png").read_bytes().startswith(b"\x89PNG")
    script = (frontend.FRONTEND_DIR / "soundsticks5-lovelace.js").read_text(encoding="utf-8")
    assert frontend.STATIC_URL + "/soundsticks5.png" in script
