# SoundSticks 5 for Home Assistant

English | [简体中文](README.md)

An unofficial, local Home Assistant solution for the Harman Kardon SoundSticks 5. This repository contains:

- `custom_components/soundsticks5`: BLE/GATT control for lighting, EQ, media actions, volume, and device settings;
- `soundsticks5_audio`: an optional Home Assistant App using host BlueZ and A2DP for wake and real audio playback.

This project is not affiliated with, authorized, sponsored, or endorsed by Harman Kardon or HARMAN International. Protocol work currently targets the standard SoundSticks 5, HK One 2.5.4, and one tested firmware/device. Other regions, SKUs, and firmware may differ.

## Highlights

- Home Assistant Bluetooth discovery without persisting a historical MAC/RPA;
- lighting power, linear `0..100` brightness, six themes, animation speed, per-theme color, and color reset;
- seven App-scale EQ controls and reset;
- feedback tone, inactivity timeout, and remaining-time state;
- BLE play/pause/previous/next, absolute volume, playback, title, and artist state;
- serialized GATT access, notifications, state readback, retry/backoff, diagnostics, translations, and HACS metadata;
- optional Audio App with BlueZ scan/pair/trust/connect/release/reconnect and A2DP wake;
- URL, HTTP stream, TTS, and local media playback through ffmpeg and PulseAudio/BlueZ;
- pause/resume/stop, a basic queue, completion events, and WebSocket state updates.

Lighting is not speaker power. A successful BLE media ACK also does not prove that deep standby ended. The currently reliable non-physical wake path is reconnecting a previously paired Classic Bluetooth A2DP/AVRCP source; the Audio App's Wake action uses that behavior.

## Installation

See [Installation](docs/installation.md). In short:

1. Install this repository as a HACS custom repository, or copy `custom_components/soundsticks5` to `/config/custom_components/`.
2. Restart Home Assistant.
3. Wake the speaker and accept Bluetooth discovery under Settings → Devices & services, or add SoundSticks 5 manually.
4. Stop here for BLE-only control. The Audio App is optional.
5. For wake and playback, add this repository as a Home Assistant App repository, install **SoundSticks Audio**, pair Classic Bluetooth once, and enable the backend in integration options. HAOS/Supervised defaults to the host gateway at `http://172.30.32.1:8099`; use an address reachable from Core for other layouts.

One host-managed physical Bluetooth adapter is the primary design target. BLE and Classic Bluetooth remain separate protocol layers, but may share that adapter. Actual concurrency depends on the adapter, BlueZ, proxy type, and speaker state.

## Safety and status

There is no arbitrary GATT write surface. OTA, firmware transfer, factory reset, unbinding, and unknown commands are intentionally absent. Diagnostics redact addresses, tokens, media sources, title, and artist.

A firmware entity is intentionally omitted because no safe and confirmed BLE query exists. Rename is also omitted from the UI despite a confirmed write frame because equivalent readback semantics are not yet established.

Protocol and API code has automated coverage. Full HAOS installation, multi-architecture images, first pairing, one-adapter BLE+A2DP concurrency, stream recovery, and format coverage remain **implemented but hardware validation required**. See [Validation status](docs/validation.md).

Protocol evidence lives in [soundsticks5-protocol](https://github.com/neqq3/soundsticks5-protocol).

## License

Apache License 2.0. See [LICENSE](LICENSE).
