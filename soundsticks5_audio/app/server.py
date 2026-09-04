"""Local HTTP/WebSocket API joining BlueZ and the audio pipeline."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from aiohttp import web

from .audio import AudioPlayer
from .bluez import BluezManager, BluezUnavailable
from .config import AppConfig


@web.middleware
async def error_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc), "error_type": type(exc).__name__}, status=400)
    except (BluezUnavailable, RuntimeError) as exc:
        return web.json_response({"ok": False, "error": str(exc), "error_type": type(exc).__name__}, status=503)


class SoundSticksAudioServer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.bluez = BluezManager(config.adapter, config.device_address, config.device_alias)
        self.websockets: set[web.WebSocketResponse] = set()
        self.player = AudioPlayer(config.sink_match, self._event, config.max_playback_seconds)
        self.reconnect_task: asyncio.Task | None = None
        self.background_tasks: set[asyncio.Task] = set()
        self.release_after_playback = config.release_after_playback
        self.release_delay = config.release_delay
        self.auto_reconnect = config.auto_reconnect

    @web.middleware
    async def auth_middleware(self, request: web.Request, handler):
        if not self.config.api_token or request.path == "/health":
            return await handler(request)
        if request.headers.get("Authorization") != f"Bearer {self.config.api_token}":
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        return await handler(request)

    async def start(self) -> web.Application:
        await self.bluez.start()
        app = web.Application(middlewares=[error_middleware, self.auth_middleware])
        app.add_routes(
            [
                web.get("/health", self.health),
                web.get("/status", self.status),
                web.get("/scan", self.scan),
                web.post("/scan", self.scan),
                web.post("/pair", self.pair),
                web.post("/connect", self.connect),
                web.post("/disconnect", self.disconnect),
                web.post("/release", self.disconnect),
                web.post("/wake", self.wake),
                web.post("/wake-release", self.wake_release),
                web.post("/play", self.play),
                web.post("/pause", self.pause),
                web.post("/resume", self.resume),
                web.post("/stop", self.stop),
                web.post("/volume", self.volume),
                web.get("/ws", self.websocket),
            ]
        )
        app.on_cleanup.append(self.cleanup)
        if self.config.auto_connect:
            self._spawn(self._connect_if_paired(), "soundsticks5 startup connect")
        self.reconnect_task = asyncio.create_task(self._reconnect_loop(), name="soundsticks5-reconnect")
        return app

    def _spawn(self, coroutine, name: str) -> None:
        task = asyncio.create_task(coroutine, name=name)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _json(self, request: web.Request) -> dict[str, Any]:
        if not request.can_read_body:
            return {}
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    async def _connect_if_paired(self) -> None:
        status = await self.bluez.status()
        if status.get("paired") and not status.get("audio_connected"):
            await self.bluez.connect()

    async def _ensure_audio(self) -> None:
        await self._connect_if_paired()
        bluez_status = await self.bluez.status()
        self.player.device_address = str(bluez_status.get("address", ""))
        for _attempt in range(20):
            if await self.player.find_sink():
                return
            await asyncio.sleep(0.5)
        raise RuntimeError("A2DP connected but no audio sink appeared")

    async def _event(self, event: str, payload: dict) -> None:
        message = {"event": event, **payload}
        for websocket in list(self.websockets):
            with contextlib.suppress(Exception):
                await websocket.send_json(message)
        if event in {"playback_completed", "playback_error"} and self.release_after_playback and not self.player.queue:
            self._spawn(self._release_after_delay(self.release_delay), "soundsticks5 delayed release")

    async def _release_after_delay(self, delay: int) -> None:
        await asyncio.sleep(max(0, delay))
        if not self.player.queue and not (self.player.task and not self.player.task.done()):
            await self.bluez.disconnect()

    async def _reconnect_loop(self) -> None:
        while True:
            await asyncio.sleep(5)
            if not self.auto_reconnect or not (self.player.task and not self.player.task.done()):
                continue
            status = await self.bluez.status()
            if not status.get("audio_connected"):
                with contextlib.suppress(Exception):
                    await self.bluez.connect()

    async def health(self, _request: web.Request) -> web.Response:
        bluez = await self.bluez.status()
        return web.json_response({"ok": True, "service": "soundsticks5-audio", "bluez": True, "device_found": bluez.get("device_found", False)})

    async def status(self, _request: web.Request) -> web.Response:
        return web.json_response({"ok": True, **await self.bluez.status(), **await self.player.status()})

    async def scan(self, request: web.Request) -> web.Response:
        payload = await self._json(request)
        return web.json_response({"ok": True, "devices": await self.bluez.scan(float(payload.get("seconds", 12)))})

    async def pair(self, request: web.Request) -> web.Response:
        payload = await self._json(request)
        await self.bluez.pair(payload.get("address"))
        return web.json_response({"ok": True, **await self.bluez.status()})

    async def connect(self, _request: web.Request) -> web.Response:
        await self.bluez.connect()
        return web.json_response({"ok": True, **await self.bluez.status()})

    async def disconnect(self, _request: web.Request) -> web.Response:
        await self.player.stop()
        await self.bluez.disconnect()
        return web.json_response({"ok": True, **await self.bluez.status()})

    async def wake(self, request: web.Request) -> web.Response:
        payload = await self._json(request)
        await self.bluez.connect()
        if not payload.get("keep_connected", True):
            self._spawn(
                self._release_after_delay(int(payload.get("delay", self.config.release_delay))),
                "soundsticks5 wake release",
            )
        return web.json_response({"ok": True, **await self.bluez.status()})

    async def wake_release(self, request: web.Request) -> web.Response:
        payload = await self._json(request)
        await self.bluez.connect()
        self._spawn(
            self._release_after_delay(int(payload.get("delay", self.config.release_delay))),
            "soundsticks5 wake release",
        )
        return web.json_response({"ok": True, **await self.bluez.status()})

    async def play(self, request: web.Request) -> web.Response:
        payload = await self._json(request)
        source = payload.get("url") or payload.get("path")
        if not isinstance(source, str) or not source:
            raise ValueError("play requires url or path")
        await self._ensure_audio()
        self.release_after_playback = bool(payload.get("release_after_playback", self.config.release_after_playback))
        self.release_delay = max(0, min(60, int(payload.get("release_delay", self.config.release_delay))))
        self.auto_reconnect = bool(payload.get("auto_reconnect", self.config.auto_reconnect))
        await self.player.play(source, title=payload.get("title"), enqueue=bool(payload.get("enqueue", False)))
        return web.json_response({"ok": True, **await self.player.status()})

    async def pause(self, _request: web.Request) -> web.Response:
        await self.player.pause()
        return web.json_response({"ok": True, **await self.player.status()})

    async def resume(self, _request: web.Request) -> web.Response:
        await self.player.resume()
        return web.json_response({"ok": True, **await self.player.status()})

    async def stop(self, _request: web.Request) -> web.Response:
        await self.player.stop()
        if self.release_after_playback:
            self._spawn(self._release_after_delay(self.release_delay), "soundsticks5 stop release")
        return web.json_response({"ok": True, **await self.player.status()})

    async def volume(self, request: web.Request) -> web.Response:
        payload = await self._json(request)
        try:
            value = int(payload["volume"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("volume requires an integer in 0..100") from exc
        if not 0 <= value <= 100:
            raise ValueError("volume requires an integer in 0..100")
        await self.player.set_volume(value)
        return web.json_response({"ok": True, **await self.player.status()})

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        websocket = web.WebSocketResponse(heartbeat=30)
        await websocket.prepare(request)
        self.websockets.add(websocket)
        await websocket.send_json({"event": "status", **await self.bluez.status(), **await self.player.status()})
        try:
            async for _message in websocket:
                pass
        finally:
            self.websockets.discard(websocket)
        return websocket

    async def cleanup(self, _app: web.Application) -> None:
        if self.reconnect_task:
            self.reconnect_task.cancel()
            await asyncio.gather(self.reconnect_task, return_exceptions=True)
        for task in self.background_tasks:
            task.cancel()
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        await self.player.stop()
        await self.bluez.stop()
        for websocket in list(self.websockets):
            await websocket.close()
