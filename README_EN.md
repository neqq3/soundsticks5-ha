# SoundSticks 5 for Home Assistant

English | [简体中文](README.md)

An unofficial, local BLE/GATT Home Assistant integration for the Harman Kardon SoundSticks 5.

This project is not affiliated with, authorized, sponsored, or endorsed by Harman Kardon or HARMAN International. Protocol work currently targets the standard SoundSticks 5, HK One 2.5.4, and one tested firmware/device. Other regions, SKUs, and firmware may differ.

## Highlights

- Home Assistant Bluetooth discovery without persisting a historical MAC/RPA;
- lighting power, linear `0..100` brightness, six themes, animation speed, per-theme color, and color reset;
- seven App-scale EQ controls and reset;
- feedback tone, inactivity timeout, and remaining-time state;
- BLE play/pause/previous/next, absolute volume, playback, title, and artist state;
- one-shot full state refresh and explicit GATT control-session release;
- serialized GATT access, notifications, authoritative media readback, retry/backoff, diagnostics, translations, and HACS metadata.

Lighting is not speaker power. A successful BLE media ACK also does not prove that playback changed, so the integration reads aggregate state back after media commands. A2DP transport and wake are intentionally outside this integration's user-facing scope; use a mature Bluetooth audio solution supported by Music Assistant if needed.

## Installation

See [Installation](docs/installation.md). In short:

1. Install this repository as a HACS custom repository, or copy `custom_components/soundsticks5` to `/config/custom_components/`.
2. Restart Home Assistant.
3. Wake the speaker and accept Bluetooth discovery under Settings → Devices & services, or add SoundSticks 5 manually.

The integration requires a connectable Home Assistant Bluetooth adapter or proxy. It does not manage Classic Bluetooth audio.

See [Entities and mappings](docs/entities.md) for complete behavior and scale mappings.

## Safety and status

There is no arbitrary GATT write surface. OTA, firmware transfer, factory reset, unbinding, and unknown commands are intentionally absent. Diagnostics redact addresses, title, and artist.

A firmware entity is intentionally omitted because no safe and confirmed BLE query exists. Rename is also omitted from the UI despite a confirmed write frame because equivalent readback semantics are not yet established.

Protocol, connection lifecycle, and entity behavior have automated coverage. Different HA Bluetooth adapters, remote proxies, and firmware combinations still require continued validation. See [Validation status](docs/validation.md).

Protocol evidence lives in [soundsticks5-protocol](https://github.com/neqq3/soundsticks5-protocol).

## License

Apache License 2.0. See [LICENSE](LICENSE).
