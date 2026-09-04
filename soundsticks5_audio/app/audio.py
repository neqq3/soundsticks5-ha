"""Async ffmpeg to PulseAudio/PipeWire playback with a minimal queue."""

from __future__ import annotations

import asyncio
import signal
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class AudioUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class QueueItem:
    source: str
    title: str | None = None
    attempts: int = 0


EventCallback = Callable[[str, dict], Awaitable[None]]


class AudioPlayer:
    def __init__(self, sink_match: str, on_event: EventCallback, max_playback_seconds: int = 21600) -> None:
        self.sink_match = sink_match.lower()
        self.on_event = on_event
        self.max_playback_seconds = max(1, max_playback_seconds)
        self.device_address = ""
        self.queue: deque[QueueItem] = deque()
        self.current: QueueItem | None = None
        self.ffmpeg: asyncio.subprocess.Process | None = None
        self.player: asyncio.subprocess.Process | None = None
        self.task: asyncio.Task | None = None
        self.paused = False
        self.volume = 100
        self.last_event = "idle"

    async def _run(self, *args: str) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise AudioUnavailable(f"command timed out: {args[0]}") from None
        return process.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")

    async def find_sink(self) -> str | None:
        code, stdout, _stderr = await self._run("pactl", "list", "short", "sinks")
        if code:
            return None
        for line in stdout.splitlines():
            columns = line.split("\t")
            sink_name = columns[1].lower() if len(columns) >= 2 else ""
            address_token = self.device_address.lower().replace(":", "_")
            if self.sink_match in sink_name and (not address_token or address_token in sink_name):
                return columns[1]
        return None

    @staticmethod
    def validate_source(source: str) -> str:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            return source
        path = Path(source).resolve()
        allowed = (Path("/media"), Path("/share"), Path("/data"))
        if not any(path == root or root in path.parents for root in allowed):
            raise ValueError("local audio must be under /media, /share or /data")
        if not path.is_file():
            raise ValueError("local audio file does not exist")
        return str(path)

    async def play(self, source: str, *, title: str | None = None, enqueue: bool = False) -> None:
        item = QueueItem(self.validate_source(source), title)
        if enqueue and self.task and not self.task.done():
            self.queue.append(item)
            await self.on_event("queued", {"title": title, "queue_length": len(self.queue)})
            return
        await self.stop(clear_queue=not enqueue)
        self.queue.append(item)
        self.task = asyncio.create_task(self._queue_worker(), name="soundsticks5-audio-queue")

    async def _queue_worker(self) -> None:
        while self.queue:
            self.current = self.queue.popleft()
            self.last_event = "playing"
            await self.on_event("playback_started", {"title": self.current.title})
            try:
                await asyncio.wait_for(self._play_one(self.current), timeout=self.max_playback_seconds)
                self.last_event = "completed"
                await self.on_event("playback_completed", {"title": self.current.title})
            except asyncio.CancelledError:
                self.last_event = "stopped"
                raise
            except (AudioUnavailable, BrokenPipeError, ConnectionError) as exc:
                if self.current.attempts < 2:
                    self.queue.appendleft(QueueItem(self.current.source, self.current.title, self.current.attempts + 1))
                    self.last_event = "retrying"
                    await self.on_event(
                        "playback_retrying",
                        {"error": type(exc).__name__, "attempt": self.current.attempts + 1},
                    )
                    await asyncio.sleep(6)
                else:
                    self.last_event = "error"
                    await self.on_event("playback_error", {"error": type(exc).__name__})
            except Exception as exc:
                self.last_event = "error"
                await self.on_event("playback_error", {"error": type(exc).__name__})
            finally:
                self.current = None
                await self._cleanup_processes()

    async def _cleanup_processes(self) -> None:
        processes = [process for process in (self.ffmpeg, self.player) if process is not None]
        for process in processes:
            if process.returncode is None:
                try:
                    if self.paused:
                        process.send_signal(signal.SIGCONT)
                    process.terminate()
                except ProcessLookupError:
                    pass
        if processes:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*(process.wait() for process in processes), return_exceptions=True),
                    timeout=3,
                )
            except TimeoutError:
                for process in processes:
                    if process.returncode is None:
                        process.kill()
                await asyncio.gather(*(process.wait() for process in processes), return_exceptions=True)
        self.ffmpeg = self.player = None

    async def _play_one(self, item: QueueItem) -> None:
        sink = await self.find_sink()
        if sink is None:
            raise AudioUnavailable("no matching Bluetooth audio sink")
        await self.set_volume(self.volume, sink=sink)
        self.ffmpeg = await asyncio.create_subprocess_exec(
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning",
            "-i", item.source, "-vn", "-f", "s16le", "-ac", "2", "-ar", "48000", "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.player = await asyncio.create_subprocess_exec(
            "paplay", "--raw", "--format=s16le", "--rate=48000", "--channels=2", f"--device={sink}",
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert self.ffmpeg.stdout is not None and self.player.stdin is not None
        assert self.ffmpeg.stderr is not None and self.player.stderr is not None
        drains = [
            asyncio.create_task(self.ffmpeg.stderr.read()),
            asyncio.create_task(self.player.stderr.read()),
        ]
        try:
            while chunk := await self.ffmpeg.stdout.read(65536):
                self.player.stdin.write(chunk)
                await self.player.stdin.drain()
        finally:
            self.player.stdin.close()
            await self.player.stdin.wait_closed()
        ffmpeg_code, player_code = await asyncio.gather(self.ffmpeg.wait(), self.player.wait())
        await asyncio.gather(*drains, return_exceptions=True)
        if ffmpeg_code or player_code:
            raise AudioUnavailable(f"audio pipeline exited with {ffmpeg_code}/{player_code}")

    async def pause(self) -> None:
        if not self.ffmpeg or self.ffmpeg.returncode is not None:
            return
        for process in (self.ffmpeg, self.player):
            if process and process.returncode is None:
                process.send_signal(signal.SIGSTOP)
        self.paused = True
        self.last_event = "paused"
        await self.on_event("playback_paused", {})

    async def resume(self) -> None:
        if not self.paused:
            return
        for process in (self.ffmpeg, self.player):
            if process and process.returncode is None:
                process.send_signal(signal.SIGCONT)
        self.paused = False
        self.last_event = "playing"
        await self.on_event("playback_resumed", {})

    async def stop(self, *, clear_queue: bool = True) -> None:
        if clear_queue:
            self.queue.clear()
        await self._cleanup_processes()
        task, self.task = self.task, None
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.current = None
        self.paused = False
        self.last_event = "stopped"

    async def set_volume(self, value: int, *, sink: str | None = None) -> None:
        self.volume = max(0, min(100, int(value)))
        sink = sink or await self.find_sink()
        if sink is None:
            raise AudioUnavailable("no matching Bluetooth audio sink")
        code, _stdout, stderr = await self._run("pactl", "set-sink-volume", sink, f"{self.volume}%")
        if code:
            raise AudioUnavailable(f"failed to set sink volume: {stderr.strip()}")

    async def status(self) -> dict:
        return {
            "playing": bool(self.task and not self.task.done() and not self.paused),
            "paused": self.paused,
            "title": self.current.title if self.current else None,
            "queue_length": len(self.queue),
            "volume": self.volume,
            "sink_available": await self.find_sink() is not None,
            "last_event": self.last_event,
        }
