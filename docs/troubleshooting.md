# Troubleshooting

## Integration cannot find the speaker

- Wake it using a previously paired A2DP source, valid AUX audio, or physical control.
- Verify Home Assistant sees a **connectable** adapter/proxy.
- Do not enter an old BLE MAC/RPA; it can rotate.
- Temporarily stop HK One if notification subscription or writes fail. Multi-central behavior varies and is not assumed exclusive.

## BLE advertises but commands fail

The integration verifies the private service before writing. A name or anonymous advertisement alone is insufficient. It does not periodically connect merely to poll state: after one startup snapshot, notifications and explicit commands drive updates. Commands get one bounded retry and share a short idle connection grace period. Inspect the BLE diagnostic entity and retry after another GATT client releases its connection. Persistent BLE is off by default because it can increase contention.

## App changes do not appear in Home Assistant

Notifications can update Home Assistant only while its GATT session is connected. Press **Refresh all states** after changing settings in HK One. Periodic polling is intentionally avoided because it would repeatedly compete for the same control connection.

## HK One cannot acquire control

Press **Release BLE control**. This closes only Home Assistant's GATT session and does not disconnect the current Bluetooth audio source. The integration also releases automatically after a short idle grace period.

## Privacy

Normal integration logs omit addresses and nearby advertisement payloads. Diagnostics redact address, title, and artist. Bluetooth host logs are outside this integration and may include device identifiers.
