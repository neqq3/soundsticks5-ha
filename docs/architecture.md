# Architecture

```text
Home Assistant entities
        │
        ├── SoundSticksCoordinator ── HA Bluetooth API ── BLE GATT
        │        └── command write + notification state/ACK
        │
        └── AudioBackendClient ── HTTP/WebSocket ── SoundSticks Audio App
                                                   ├── host BlueZ D-Bus
                                                   └── ffmpeg → paplay → A2DP
```

BLE control and Classic Bluetooth audio are deliberately independent. If the App is absent, every BLE entity continues to work. If BLE is temporarily unavailable but the App is healthy, audio controls remain available. Both appear under one Home Assistant device registry entry.

## BLE identity and lifecycle

The integration matches the confirmed private control service UUID. It retains Home Assistant's current `BLEDevice`, not a copied address. On every candidate connection it enumerates services and rejects the device unless the private service exists. A conservative anonymous-standby fallback may notice observed Fast Pair service data, but it never sends a command before service verification.

Commands and queries share one lock. Each operation connects, subscribes to notifications, writes an allow-listed frame, waits for the matching ACK or state response, and normally disconnects. Transient Bleak/OS/time-out errors trigger bounded exponential backoff. Keeping BLE connected is optional because persistent ownership can increase contention with HK One or another central.

## State authority

Entity setters do not treat a write as final UI state. The coordinator processes notifications and immediately performs a full query refresh after commands. ACK only confirms acceptance; this distinction matters for play without an active audio stream and for standby behavior.

## Audio App

The App uses host BlueZ over D-Bus for discovery, pairing, trust, connect, and disconnect. It registers a no-input/no-output pairing agent limited to standard audio profiles. Audio is decoded to stereo 48 kHz signed 16-bit PCM and streamed to the selected PulseAudio BlueZ sink. The sink name, adapter, and target can all be configured; `hci0` and a fixed MAC are not assumed.

The HTTP API is request/response control. WebSocket events provide low-latency state transitions to the integration. Both components use their own tasks and never call each other while holding a BLE GATT lock.

