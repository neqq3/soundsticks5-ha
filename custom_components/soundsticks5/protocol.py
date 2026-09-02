"""Minimal confirmed SoundSticks 5 protocol helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from .const import THEMES


class ProtocolError(ValueError):
    """Raised when a received application frame is malformed."""


@dataclass(slots=True)
class LightState:
    """Known lighting state."""

    power: bool | None = None
    brightness: int | None = None
    speed: int | None = None
    theme_id: int | None = None
    colors: dict[int, int] = field(default_factory=dict)


def frame(cmd: int, data: bytes = b"") -> bytes:
    if len(data) > 255:
        raise ValueError("data is too long")
    return bytes((0xAA, cmd, len(data))) + data


def tlv(tag: int, value: bytes) -> bytes:
    if len(value) > 255:
        raise ValueError("TLV value is too long")
    return bytes((tag, len(value))) + value


def set_light_power(on: bool) -> bytes:
    return frame(0x33, b"\x00" + tlv(0x99, bytes((1 if on else 0,))))


def set_brightness(value: int) -> bytes:
    value = max(0, min(100, int(value)))
    return frame(0x33, b"\x00" + tlv(0x45, bytes((value,))))


def set_speed(value: int) -> bytes:
    if value not in (1, 2, 3):
        raise ValueError("speed must be 1, 2 or 3")
    return frame(0x33, b"\x00" + tlv(0x4D, bytes((value,))))


def set_theme(name: str) -> bytes:
    theme_id, default_color = THEMES[name]
    data = b"\x00" + tlv(0x4F, bytes((theme_id,))) + tlv(0x4C, bytes((theme_id, default_color)))
    return frame(0x33, data)


def set_color(theme_id: int, value: int) -> bytes:
    value = max(0, min(100, int(value)))
    return frame(0x33, b"\x00" + tlv(0x4C, bytes((theme_id, value))))


def parse_light_state(raw: bytes) -> LightState:
    if len(raw) < 3 or raw[0] != 0xAA:
        raise ProtocolError("not an AA application frame")
    cmd, length = raw[1], raw[2]
    if cmd != 0x32:
        raise ProtocolError(f"expected 0x32 light-state frame, got 0x{cmd:02x}")
    if len(raw) < 3 + length:
        raise ProtocolError("truncated frame")
    data = raw[3 : 3 + length]
    if data[:1] == b"\x00":
        data = data[1:]

    state = LightState()
    offset = 0
    while offset + 2 <= len(data):
        tag = data[offset]
        size = data[offset + 1]
        offset += 2
        if offset + size > len(data):
            raise ProtocolError("truncated TLV")
        value = data[offset : offset + size]
        offset += size
        if tag == 0x99 and size == 1:
            state.power = bool(value[0])
        elif tag == 0x45 and size == 1:
            state.brightness = value[0]
        elif tag == 0x4D and size == 1:
            state.speed = value[0]
        elif tag == 0x4F and size == 1:
            state.theme_id = value[0]
        elif tag == 0x4C and size == 2:
            state.colors[value[0]] = value[1]
    return state
