# Architecture

```text
Home Assistant entities
                    │
                    ▼
          SoundSticksCoordinator
                    │
        serialized command + query
                    │
                    ▼
        Home Assistant Bluetooth API
                    │
                    ▼
                 BLE GATT
```

## BLE identity and lifecycle

The integration matches the confirmed private control service UUID. It retains Home Assistant's current `BLEDevice`, not a copied address. On every candidate connection it enumerates services and rejects the device unless the private service exists. A conservative anonymous-standby fallback may notice observed Fast Pair service data, but it never sends a command before service verification.

Commands and queries share one lock. The integration takes one state snapshot at startup and does not periodically acquire GATT merely to poll. Each operation connects if needed, subscribes to notifications, writes only allow-listed frames, and waits for a matching ACK or state response. A short idle grace period lets a command burst reuse one session before automatic release; **Release BLE control** closes it immediately. Transient Bleak/OS/time-out errors get one bounded retry.

## State authority

The coordinator applies unsolicited notifications directly to its cache while connected. **Refresh all states** explicitly requests lighting, aggregate media, feedback tone, auto-off and EQ snapshots, mirroring the state groups requested when HK One's product page mounts.

For media actions, an ACK proves only that the private command was accepted. The coordinator therefore queries aggregate media state after every play, pause, previous, next or volume action. The combined play/pause action first queries current playback, chooses the opposite command, and queries again after the ACK.

A new RPA advertisement never tears down a still-valid session; the latest discovered address is used after that session ends. Classic Bluetooth audio and wake are intentionally outside the integration architecture.
