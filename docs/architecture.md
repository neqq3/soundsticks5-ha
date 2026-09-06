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

Commands and queries share one lock. The integration takes one state snapshot at startup and does not periodically open GATT to poll. Each explicit operation connects if needed, subscribes to notifications, writes an allow-listed frame, and waits for the matching ACK or state response. A short idle grace period lets a burst reuse one session before it disconnects. Transient Bleak/OS/time-out errors get one bounded retry. Keeping BLE connected is optional because persistent ownership can increase contention with HK One or another central.

## State authority

Entity setters do not treat a host-side write as success: the coordinator requires a matching protocol ACK or state response and applies notifications directly to its cache. It does not perform a five-query refresh after every command. A new RPA advertisement never tears down a still-valid session; the latest discovered address is used after that session ends. ACK only confirms acceptance, not a physical wake or successful media playback.

## Audio App

The App uses host BlueZ over D-Bus for discovery, pairing, trust, connect, and disconnect. It registers a no-input/no-output pairing agent limited to standard audio profiles. Audio is decoded to stereo 48 kHz signed 16-bit PCM and streamed to the selected PulseAudio BlueZ sink. The sink name, adapter, and target can all be configured; `hci0` and a fixed MAC are not assumed.

The HTTP API is request/response control. WebSocket events provide low-latency state transitions to the integration. Both components use their own tasks and never call each other while holding a BLE GATT lock.
