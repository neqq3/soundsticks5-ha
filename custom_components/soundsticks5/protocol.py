"""Confirmed SoundSticks 5 application protocol (no arbitrary writes)."""

from __future__ import annotations

import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from .const import AUTO_OFF_SECONDS, EQ_FREQUENCIES, SPEEDS, THEMES


class ProtocolError(ValueError):
    """Raised when a frame is malformed or outside the confirmed allow-list."""


@dataclass(frozen=True, slots=True)
class TLV:
    tag: int
    value: bytes


@dataclass(frozen=True, slots=True)
class Frame:
    command: int
    data: bytes
    separator: int | None = None

    def tlvs(self) -> list[TLV]:
        if self.command not in (0x32, 0x33, 0x42) or not self.data:
            return []
        return parse_tlvs(self.data[1:])


@dataclass(slots=True)
class DeviceState:
    light_power: bool | None = None
    brightness: int | None = None
    speed: int | None = None
    theme_id: int | None = None
    colors: dict[int, int] = field(default_factory=dict)
    playback: int | None = None
    volume: int | None = None
    track_title: str | None = None
    artist: str | None = None
    unknown_36: int | None = None
    feedback_tone: bool | None = None
    auto_off_configured: int | None = None
    auto_off_remaining: int | None = None
    eq_gains_db: list[float] | None = None
    last_ack_command: int | None = None
    last_ack_result: int | None = None


def encode_frame(command: int, data: bytes = b"") -> bytes:
    if not 0 <= command <= 0xFF or len(data) > 0xFF:
        raise ProtocolError("command and payload must fit one-byte fields")
    prefix = bytes((0xAA, command, len(data)))
    if command in (0xE2, 0xE3):
        prefix += b"\x00"
    return prefix + data


def decode_frame(raw: bytes) -> Frame:
    if len(raw) < 3 or raw[0] != 0xAA:
        raise ProtocolError("not an AA/CMD/LEN frame")
    command, length = raw[1], raw[2]
    start, separator = 3, None
    if command in (0xE2, 0xE3):
        if len(raw) < 4 or raw[3] != 0:
            raise ProtocolError("EQ frame is missing its 00 separator")
        start, separator = 4, 0
    if len(raw) != start + length:
        raise ProtocolError("frame length does not match LEN")
    return Frame(command, raw[start:], separator)


def encode_tlvs(items: Iterable[TLV]) -> bytes:
    data = bytearray()
    for item in items:
        if not 0 <= item.tag <= 0xFF or len(item.value) > 0xFF:
            raise ProtocolError("TLV does not fit one-byte fields")
        data.extend((item.tag, len(item.value)))
        data.extend(item.value)
    return bytes(data)


def parse_tlvs(data: bytes) -> list[TLV]:
    items: list[TLV] = []
    offset = 0
    while offset < len(data):
        if offset + 2 > len(data):
            raise ProtocolError("truncated TLV header")
        tag, length = data[offset], data[offset + 1]
        offset += 2
        if offset + length > len(data):
            raise ProtocolError("truncated TLV value")
        items.append(TLV(tag, data[offset : offset + length]))
        offset += length
    return items


def _percent(value: int) -> int:
    if not 0 <= int(value) <= 100:
        raise ProtocolError("value must be in 0..100")
    return int(value)


def _setting(*items: TLV) -> bytes:
    return encode_frame(0x33, b"\x00" + encode_tlvs(items))


def build_light_power(enabled: bool) -> bytes:
    return _setting(TLV(0x99, bytes((int(enabled),))))


def build_brightness(value: int) -> bytes:
    return _setting(TLV(0x45, bytes((_percent(value),))))


def build_speed(value: str | int) -> bytes:
    level = SPEEDS.get(value, value) if isinstance(value, str) else value
    if level not in (1, 2, 3):
        raise ProtocolError("speed must be low/medium/high")
    return _setting(TLV(0x4D, bytes((int(level),))))


def build_theme(name: str) -> bytes:
    try:
        theme_id, default_color = THEMES[name]
    except KeyError as exc:
        raise ProtocolError("unknown theme") from exc
    return _setting(TLV(0x4F, bytes((theme_id,))), TLV(0x4C, bytes((theme_id, default_color))))


def build_color(theme_id: int, value: int) -> bytes:
    if theme_id not in {item[0] for item in THEMES.values()}:
        raise ProtocolError("unknown theme id")
    return _setting(TLV(0x4F, bytes((theme_id,))), TLV(0x4C, bytes((theme_id, _percent(value)))))


def build_color_reset(theme_id: int) -> bytes:
    if theme_id not in {item[0] for item in THEMES.values()}:
        raise ProtocolError("unknown theme id")
    return _setting(TLV(0x50, bytes((theme_id,))))


def build_media_action(action: str) -> bytes:
    values = {"pause": 1, "play": 2, "previous": 3, "next": 4}
    if action not in values:
        raise ProtocolError("unknown media action")
    return encode_frame(0x43, b"\x00" + encode_tlvs((TLV(0x41, bytes((values[action],))),)))


def build_volume(value: int) -> bytes:
    return encode_frame(0x43, b"\x00" + encode_tlvs((TLV(0x42, bytes((_percent(value),))),)))


def build_feedback_tone(enabled: bool) -> bytes:
    return encode_frame(0xF3, bytes((int(enabled),)))


def build_auto_off(value: str | int) -> bytes:
    seconds = AUTO_OFF_SECONDS.get(value, value) if isinstance(value, str) else value
    if seconds not in AUTO_OFF_SECONDS.values():
        raise ProtocolError("unsupported auto-off duration")
    return encode_frame(0xBA, struct.pack("<H", int(seconds)))


EQ_Q = (0.707, 2.0, 2.0, 2.0, 2.0, 2.0, 0.707)
EQ_FILTER_TYPES = (0, 1, 1, 1, 1, 1, 2)
EQ_BODY_PREFIX = bytes.fromhex("c2 07 80 bb 00 00")


def app_eq_step_to_gain_db(index: int, step: int) -> float:
    if not 0 <= index < 7 or not -12 <= step <= 12:
        raise ProtocolError("EQ index/step is outside the App scale")
    gain = step / 2.0
    return gain * 1.5 if index == 0 and gain < 0 else gain


def gain_db_to_app_eq_step(index: int, gain: float) -> int:
    raw = gain / 0.75 if index == 0 and gain < 0 else gain * 2.0
    return max(-12, min(12, round(raw)))


def build_eq(steps: Sequence[int]) -> bytes:
    if len(steps) != 7:
        raise ProtocolError("EQ requires exactly seven App steps")
    body = bytearray(EQ_BODY_PREFIX)
    for index, (frequency, q_value, filter_type) in enumerate(zip(EQ_FREQUENCIES, EQ_Q, EQ_FILTER_TYPES, strict=True)):
        body.append(filter_type)
        body.extend(struct.pack("<fff", app_eq_step_to_gain_db(index, int(steps[index])), frequency, q_value))
    return encode_frame(0xE3, bytes(body))


def build_eq_reset() -> bytes:
    return build_eq((0,) * 7)


def build_rename(name: str) -> bytes:
    encoded = name.encode("utf-8")
    if not 1 <= len(encoded) <= 252:
        raise ProtocolError("UTF-8 name must occupy 1..252 bytes")
    return encode_frame(0x13, b"\x00\xC1" + bytes((len(encoded),)) + encoded)


def apply_notification(state: DeviceState, raw: bytes) -> Frame:
    """Parse one notification and merge every confirmed field into state."""
    parsed = decode_frame(raw)
    if parsed.command == 0x00 and len(parsed.data) == 2:
        state.last_ack_command, state.last_ack_result = parsed.data
    elif parsed.command == 0x32:
        for item in parsed.tlvs():
            if item.tag == 0x99 and len(item.value) == 1:
                state.light_power = bool(item.value[0])
            elif item.tag == 0x45 and len(item.value) == 1:
                state.brightness = item.value[0]
            elif item.tag == 0x4D and len(item.value) == 1:
                state.speed = item.value[0]
            elif item.tag == 0x4F and len(item.value) == 1:
                state.theme_id = item.value[0]
            elif item.tag == 0x4C and len(item.value) == 2:
                state.colors[item.value[0]] = item.value[1]
    elif parsed.command == 0x42:
        for item in parsed.tlvs():
            if item.tag == 0x41 and len(item.value) == 1 and item.value[0] in (1, 2):
                state.playback = item.value[0]
            elif item.tag == 0x42 and len(item.value) == 1:
                state.volume = min(item.value[0], 100)
            elif item.tag == 0x44:
                state.track_title = item.value.decode("utf-8", errors="replace") or None
            elif item.tag == 0x45:
                state.artist = item.value.decode("utf-8", errors="replace") or None
            elif item.tag == 0x36 and len(item.value) == 1:
                state.unknown_36 = item.value[0]
    elif parsed.command == 0xF2 and len(parsed.data) == 1 and parsed.data[0] in (0, 1):
        state.feedback_tone = bool(parsed.data[0])
    elif parsed.command == 0xB9 and len(parsed.data) == 4:
        state.auto_off_configured, state.auto_off_remaining = struct.unpack("<HH", parsed.data)
    elif parsed.command == 0xE2:
        body = parsed.data[1:] if len(parsed.data) == 98 and parsed.data[:1] == b"\xC2" else parsed.data
        if len(body) != 97 or body[:6] != EQ_BODY_PREFIX:
            raise ProtocolError("unexpected EQ snapshot layout")
        gains: list[float] = []
        for index in range(7):
            offset = 6 + index * 13
            filter_type = body[offset]
            gain, frequency, q_value = struct.unpack_from("<fff", body, offset + 1)
            if filter_type != EQ_FILTER_TYPES[index] or round(frequency) != EQ_FREQUENCIES[index] or abs(q_value - EQ_Q[index]) > 0.01:
                raise ProtocolError("unexpected EQ filter layout")
            gains.append(gain)
        state.eq_gains_db = gains
    return parsed
