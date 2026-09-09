# Installation

For an end-to-end walkthrough including the Lovelace card, see [第一次使用](getting-started.md).

## BLE integration

### HACS

1. HACS → Integrations → Custom repositories.
2. Add `https://github.com/neqq3/soundsticks5-ha` as an Integration.
3. Install SoundSticks 5 and restart Home Assistant.
4. Wake the speaker, then accept Bluetooth discovery or use Add integration.

### Manual

Copy `custom_components/soundsticks5` to `/config/custom_components/soundsticks5`, restart, and add the integration from Devices & services.

Home Assistant must have a connectable local Bluetooth adapter or a connectable Bluetooth proxy. Advertisement-only proxies cannot carry GATT commands.

## Bluetooth audio

This integration controls the private BLE protocol only. It does not install an A2DP bridge, expose wake controls, or send audio. Pair it with a separate Bluetooth audio solution when required.
