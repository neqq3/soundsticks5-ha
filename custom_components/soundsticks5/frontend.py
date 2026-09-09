"""Serve the bundled card and register its Lovelace resource."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).parent / "frontend"
STATIC_URL = "/soundsticks5/frontend"
CARD_URL = f"{STATIC_URL}/soundsticks5-lovelace.js"
LEGACY_URL = "/local/soundsticks5-lovelace.js"


def _asset_version() -> str:
    """Invalidate browser caches whenever either bundled asset changes."""
    digest = hashlib.sha256()
    for name in ("soundsticks5-lovelace.js", "soundsticks5.png"):
        digest.update((FRONTEND_DIR / name).read_bytes())
    return digest.hexdigest()[:16]


async def async_register_resource(resources, url: str) -> None:
    """Migrate only this card's resources, leaving other resources untouched."""
    if not isinstance(resources, ResourceStorageCollection):
        _LOGGER.info("YAML resources: add %s as a module to your Lovelace resources", CARD_URL)
        return
    await resources.async_get_info()
    matches = []
    for item in resources.async_items():
        parsed = urlsplit(item.get("url", ""))
        if not parsed.scheme and not parsed.netloc and parsed.path in (CARD_URL, LEGACY_URL):
            matches.append(item)
    if not matches:
        await resources.async_create_item({"url": url, "res_type": "module"})
        return
    first, *duplicates = matches
    if first["url"] != url or first.get("type") != "module":
        await resources.async_update_item(first["id"], {"url": url, "res_type": "module"})
    for item in duplicates:
        await resources.async_delete_item(item["id"])


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Called once from integration setup, before any device connections."""
    version = await hass.async_add_executor_job(_asset_version)
    # No long-lived HTTP cache: YAML users may use the URL without a version.
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), False)]
    )
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return
    resources = lovelace.resources if hasattr(lovelace, "resources") else lovelace["resources"]
    try:
        await async_register_resource(resources, f"{CARD_URL}?v={version}")
    except Exception:
        # A resource-storage problem must not prevent BLE controls from loading.
        _LOGGER.exception("Could not register the SoundSticks card; add %s as a module manually", CARD_URL)
