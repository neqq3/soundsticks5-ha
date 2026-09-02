# SoundSticks 5 for Home Assistant

Unofficial Home Assistant integration for the Harman Kardon SoundSticks 5 BLE/GATT control plane.

> This project is not affiliated with, authorized, sponsored, or endorsed by Harman Kardon or HARMAN International. Product names and trademarks belong to their respective owners.

## Current scope

This first release focuses on the confirmed BLE control protocol from [`neqq3/soundsticks5-protocol`](https://github.com/neqq3/soundsticks5-protocol):

- automatic Home Assistant Bluetooth discovery by the private control service UUID;
- rotating BLE private-address handling by refreshing the current advertisement instead of storing a historical MAC/RPA;
- lighting power;
- brightness (`0..100` protocol range, exposed through Home Assistant's normal light brightness control);
- six lighting themes;
- lighting animation speed (low / medium / high);
- per-theme color parameter (`0..100`);
- periodic state refresh;
- short-lived GATT sessions so the integration does not intentionally hold the speaker connection when idle.

The integration intentionally does **not** implement a generic arbitrary-write interface.

## Not in v0.1

Bluetooth audio (A2DP), Music Assistant playback, EQ editing, firmware/OTA, factory reset and App product-matching automation are not implemented yet. A2DP/MA belongs to a separate audio path from the BLE control protocol and will be evaluated independently before being added to this repository.

## Installation

Copy `custom_components/soundsticks5` into your Home Assistant configuration directory:

```text
/config/custom_components/soundsticks5
```

Restart Home Assistant, then open **Settings → Devices & services**. If the speaker is advertising and a Home Assistant Bluetooth adapter/proxy can see it, Home Assistant should offer the integration through Bluetooth discovery.

For the initial release, only one SoundSticks 5 entry is supported because no stable per-unit identity independent of the rotating BLE address has been confirmed yet.

## Entities

- **Light** — lighting on/off and brightness
- **Theme** — Ocean, Aurora, Blossom, Sunrise, Fireplace, Static
- **Speed** — Low, Medium, High
- **Color parameter** — integer `0..100` for the currently selected theme

The color parameter is a device protocol value, not RGB/HSV.

## Connection model

The speaker has been observed using rotating BLE random private addresses. This integration does not treat an old MAC/RPA as device identity. Home Assistant Bluetooth advertisements refresh the current `BLEDevice`; commands connect to that current object, perform the requested GATT operation, and disconnect.

A query is sent by **GATT Write** to the command characteristic and answered by notification. When documentation calls it a “read-only query”, that means the protocol operation is intended to query state without changing settings; it does not mean an ATT/GATT Read request.

## Audio / Music Assistant roadmap

SoundSticks 5 control and audio use different Bluetooth layers:

- control: BLE GATT;
- audio: classic Bluetooth A2DP/AVRCP.

The likely MA path is therefore an audio bridge/player layer rather than pretending A2DP is part of the HA BLE integration. Existing Music Assistant/Sendspin Bluetooth bridge options should be tested first; SoundSticks-specific audio code is only justified where its reconnect, wake, release-to-AUX or lifecycle behaviour needs custom handling.

## Protocol source

Protocol research, evidence levels and reproducibility tools live in:

- https://github.com/neqq3/soundsticks5-protocol

Please report protocol disagreements there with device/SKU/firmware context when possible.

## License

Apache License 2.0. See [LICENSE](LICENSE).
