# Troubleshooting

## Integration cannot find the speaker

- Wake it using a previously paired A2DP source, valid AUX audio, or physical control.
- Verify Home Assistant sees a **connectable** adapter/proxy.
- Do not enter an old BLE MAC/RPA; it can rotate.
- Temporarily stop HK One if notification subscription or writes fail. Multi-central behavior varies and is not assumed exclusive.

## BLE advertises but commands fail

The integration verifies the private service before writing. A name or anonymous advertisement alone is insufficient. It does not periodically connect merely to poll state: after one startup snapshot, notifications and explicit commands drive updates. Commands get one bounded retry and share a short idle connection grace period. Inspect the BLE diagnostic entity and retry after another GATT client releases its connection. Persistent BLE is off by default because it can increase contention.

## Wake does nothing

Wake requires one successful Classic Bluetooth pairing. BLE play/next/light commands are not reliable wake commands. Confirm `/status` reports `paired=true`; pairing mode is only needed for first pairing.

## BlueZ connects but no audio sink appears

- Confirm `audio_connected=true` and `a2dp_sink=true`.
- Check that the host created a `bluez_output...` PulseAudio/PipeWire sink.
- Adjust `sink_match` only for multiple sinks or different naming.
- Container/Core users must mount system D-Bus and the audio socket themselves.

## AUX does not take over

Press **Release Bluetooth Audio** or enable release-after-playback. A connected A2DP source may retain priority while silent.

## Audio is too loud

Set volume before playback. Initial hardware validation should use silence or a low-level file. BLE volume is direct `0..100`, not AVRCP `0..127`.

## Privacy

Normal integration logs omit addresses and nearby advertisement payloads. Diagnostics redact address, token, media source, title, and artist. BlueZ system logs are outside this integration and may include device identifiers.
