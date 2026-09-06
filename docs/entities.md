# Entities and mappings

## Media

BLE supports play, pause, previous, next, and absolute `0..100` volume. State, title, and artist come from aggregate notifications/query. Previous/next are actions and are never cached as state.

The combined play/pause action follows HK One's high-level behavior: refresh aggregate state, choose the opposite action, send it, then query aggregate state again. Explicit play, pause, previous, next and volume actions also read aggregate state back after the matching `0x43` ACK. An ACK alone is not presented as proof that the A2DP player changed state.

## Lighting

- **Lighting:** lamp state and linear brightness. HA `0..255` maps to protocol `0..100`.
- **Lighting brightness:** a dedicated App-scale `0..100%` slider, in addition to the standard HA light control.
- **Lighting theme:** Ocean/碧波荡漾 `0x10`, Aurora/极光幻境 `0x11`, Blossom/落英缤纷 `0x12`, Sunrise/旭日东升 `0x13`, Fireplace/雪夜炉火 `0x14`, Static/静谧时光 `0x15`.
- **Lighting speed:** Low/Medium/High map to `1/2/3`.
- **Current theme color:** integer `0..100`; an App parameter, not RGB/HSV.
- **Reset current theme color:** resets the current theme only.

Observed defaults are 54/50/75/60/72/0 in the order above. Theme selection follows HK One by sending both theme and default color.

## EQ

The seven sliders match HK One's 25 positions from `-12` to `+12`, not literal dB labels. Most positions represent 0.5 dB. The 125 Hz negative half uses the App-confirmed 1.5× compensation. Every write sends the complete seven-filter snapshot. Reset sends seven zero gains directly.

Slider updates are coalesced with a 300 ms trailing debounce so superseded positions are not replayed over a remote Bluetooth proxy. Since captured `0xe3` writes do not provide a dependable application ACK, the integration explicitly queries `e1` after writing and accepts the change only when the returned `e2` snapshot matches.

## Device settings

- **Feedback tone:** queried and confirmed from the device.
- **Auto-off:** Never, 10 minutes, 1 hour, 2 hours, 4 hours.
- **Auto-off remaining:** device-reported seconds; zero alone does not prove BLE has disappeared.

## State and connection actions

- **Refresh all states:** requests lighting, aggregate media, feedback tone, auto-off and EQ snapshots in one serialized GATT session. This is the explicit synchronization action after settings were changed in HK One while Home Assistant was disconnected.
- **Release BLE control:** immediately closes Home Assistant's GATT session. It does not affect Classic Bluetooth audio.

The integration normally releases GATT after a short idle grace period. It deliberately avoids periodic polling because repeatedly acquiring the control connection increases contention with HK One and remote Bluetooth proxies.
