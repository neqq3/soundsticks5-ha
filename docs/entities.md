# Entities and mappings

## Lighting

- **Lighting:** lamp state and linear brightness. HA `0..255` maps to protocol `0..100`.
- **Lighting theme:** Ocean `0x10`, Aurora `0x11`, Blossom `0x12`, Sunrise `0x13`, Fireplace `0x14`, Static `0x15`.
- **Lighting speed:** Low/Medium/High map to `1/2/3`.
- **Current theme color:** integer `0..100`; an App parameter, not RGB/HSV.
- **Reset current theme color:** resets the current theme only.

Observed defaults are 54/50/75/60/72/0 in the order above. Theme selection follows HK One by sending both theme and default color.

## EQ

The seven sliders match HK One's 25 positions from `-12` to `+12`, not literal dB labels. Most positions represent 0.5 dB. The 125 Hz negative half uses the App-confirmed 1.5× compensation. Every write sends the complete seven-filter snapshot. Reset sends seven zero gains, equivalent to Reset followed by the App's confirmation check mark.

## Media

BLE supports play, pause, previous, next, and absolute `0..100` volume. State, title, and artist come from aggregate notifications/query. Previous/next are actions and are never cached as state. With the Audio App, `play_media` accepts URL/TTS/local-media sources.

## Device settings

- **Feedback tone:** queried and confirmed from the device.
- **Auto-off:** Never, 10 minutes, 1 hour, 2 hours, 4 hours.
- **Auto-off remaining:** device-reported seconds; zero alone does not prove BLE has disappeared.

## Audio and wake

- **Bluetooth audio connected:** Classic Bluetooth from BlueZ, not the unknown private `0x36` byte.
- **Wake speaker:** establishes a previously paired A2DP connection.
- **Release Bluetooth audio:** stops backend playback and disconnects A2DP for AUX/another source.

Wake behavior: `wake_only` connects then immediately releases; `wake_release` waits the configured delay; `wake_keep_connected` retains A2DP.

