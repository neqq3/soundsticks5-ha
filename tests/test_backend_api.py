from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from soundsticks5_audio.app.config import AppConfig
from soundsticks5_audio.app.server import SoundSticksAudioServer


@pytest.fixture
async def client():
    service = SoundSticksAudioServer(AppConfig())
    service.bluez.start = AsyncMock()
    service.bluez.status = AsyncMock(return_value={"device_found": True, "paired": True, "audio_connected": False})
    service.bluez.connect = AsyncMock()
    service.bluez.disconnect = AsyncMock()
    service.bluez.stop = AsyncMock()
    service.player.status = AsyncMock(return_value={"playing": False, "paused": False, "volume": 100})
    app = await service.start()
    async with TestClient(TestServer(app)) as test_client:
        yield test_client, service


async def test_health_and_status_contract(client):
    test_client, _service = client
    response = await test_client.get("/health")
    assert response.status == 200
    assert (await response.json())["service"] == "soundsticks5-audio"
    response = await test_client.get("/status")
    body = await response.json()
    assert body["ok"] is True
    assert body["paired"] is True
    websocket = await test_client.ws_connect("/ws")
    event = await websocket.receive_json()
    assert event["event"] == "status"
    await websocket.close()


async def test_wake_release_and_disconnect_contract(client):
    test_client, service = client
    response = await test_client.post("/wake-release", json={"delay": 0})
    assert response.status == 200
    service.bluez.connect.assert_awaited_once()
    response = await test_client.post("/disconnect")
    assert response.status == 200
    service.bluez.disconnect.assert_awaited()


async def test_volume_validation(client):
    test_client, _service = client
    response = await test_client.post("/volume", json={"volume": 101})
    assert response.status == 400
    assert (await response.json())["error_type"] == "ValueError"
