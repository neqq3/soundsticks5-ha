import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("homeassistant")

from custom_components.soundsticks5.coordinator import SoundSticksCoordinator
from custom_components.soundsticks5.protocol import DeviceState


async def test_live_connection_survives_new_rpa_advertisement():
    coordinator = SoundSticksCoordinator.__new__(SoundSticksCoordinator)
    coordinator._disconnect_task = None
    coordinator.ble_device = SimpleNamespace(address="new-rpa")
    live_client = SimpleNamespace(address="old-rpa", is_connected=True)
    coordinator._client = live_client

    assert await coordinator._ensure_connected() is live_client


async def test_command_uses_notification_cache_without_full_refresh():
    coordinator = SoundSticksCoordinator.__new__(SoundSticksCoordinator)
    coordinator._io_lock = asyncio.Lock()
    coordinator._with_retries = AsyncMock(return_value=object())
    coordinator._write_wait = AsyncMock()
    coordinator._schedule_disconnect = Mock()
    coordinator.async_set_updated_data = Mock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator.state = DeviceState()

    await coordinator.async_command(
        b"request",
        ack_command=0x33,
        state_update=lambda state: setattr(state, "light_power", False),
    )

    coordinator._schedule_disconnect.assert_called_once_with()
    assert coordinator.state.light_power is False
    coordinator.async_set_updated_data.assert_called_once_with(coordinator.state)
    coordinator.async_request_refresh.assert_not_awaited()


async def test_retry_budget_is_two_attempts(monkeypatch):
    coordinator = SoundSticksCoordinator.__new__(SoundSticksCoordinator)
    coordinator.last_ble_error = None
    coordinator.ble_status = "connected"
    coordinator._disconnect = AsyncMock()
    operation = AsyncMock(side_effect=[TimeoutError, "ok"])
    sleep = AsyncMock()
    monkeypatch.setattr("custom_components.soundsticks5.coordinator.asyncio.sleep", sleep)

    assert await coordinator._with_retries(operation) == "ok"
    assert operation.await_count == 2
    coordinator._disconnect.assert_awaited_once_with()
    sleep.assert_awaited_once_with(1.5)


async def test_eq_slider_coalesces_superseded_positions(monkeypatch):
    coordinator = SoundSticksCoordinator.__new__(SoundSticksCoordinator)
    coordinator._io_lock = asyncio.Lock()
    coordinator._eq_revision = 0
    coordinator._desired_eq_steps = None
    coordinator.state = DeviceState(eq_gains_db=[0.0] * 7)
    coordinator._write_eq_and_verify_locked = AsyncMock()

    async def run_operation(operation):
        return await operation()

    coordinator._with_retries = AsyncMock(side_effect=run_operation)
    coordinator._schedule_disconnect = Mock()
    coordinator.async_set_updated_data = Mock()

    sleep_started = asyncio.Event()
    both_sleeping = asyncio.Event()
    release_sleep = asyncio.Event()
    sleep_count = 0

    async def controlled_sleep(_seconds):
        nonlocal sleep_count
        sleep_count += 1
        sleep_started.set()
        if sleep_count == 2:
            both_sleeping.set()
        await release_sleep.wait()

    monkeypatch.setattr("custom_components.soundsticks5.coordinator.asyncio.sleep", controlled_sleep)
    first = asyncio.create_task(coordinator.async_set_eq_band(0, -2))
    await sleep_started.wait()
    second = asyncio.create_task(coordinator.async_set_eq_band(0, -6))
    await both_sleeping.wait()
    release_sleep.set()
    await asyncio.gather(first, second)

    coordinator._write_eq_and_verify_locked.assert_awaited_once()
    assert coordinator._write_eq_and_verify_locked.await_args.args[0][0] == -6
