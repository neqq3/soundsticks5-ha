"""Client for the optional SoundSticks Audio App."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import ClientError, ClientTimeout, ClientWSTimeout, WSMsgType
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class BackendUnavailable(RuntimeError):
    """Raised when the optional audio backend cannot be reached."""


class AudioBackendClient:
    def __init__(self, hass, base_url: str, token: str = "") -> None:
        self._session = async_get_clientsession(hass)
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                json=payload,
                headers=self._headers,
                timeout=ClientTimeout(total=10),
            ) as response:
                if response.status >= 400:
                    raise BackendUnavailable(f"audio backend returned HTTP {response.status}")
                return await response.json()
        except (ClientError, TimeoutError, ValueError) as exc:
            raise BackendUnavailable("audio backend is unavailable") from exc

    async def status(self) -> dict[str, Any]:
        return await self.request("GET", "/status")

    async def action(self, action: str, **payload: Any) -> dict[str, Any]:
        return await self.request("POST", f"/{action}", payload)

    async def listen(
        self,
        callback: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Stream backend status events, reconnecting until cancelled."""
        delay = 1.0
        while True:
            try:
                async with self._session.ws_connect(
                    f"{self._base_url}/ws",
                    headers=self._headers,
                    heartbeat=30,
                    timeout=ClientWSTimeout(ws_close=10),
                ) as websocket:
                    delay = 1.0
                    async for message in websocket:
                        if message.type == WSMsgType.TEXT:
                            payload = message.json()
                            if isinstance(payload, dict):
                                await callback(payload)
                        elif message.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                            break
            except asyncio.CancelledError:
                raise
            except (ClientError, TimeoutError, ValueError):
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
