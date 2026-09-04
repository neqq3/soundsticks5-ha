# Installation

## BLE integration

### HACS

1. HACS → Integrations → Custom repositories.
2. Add `https://github.com/neqq3/soundsticks5-ha` as an Integration.
3. Install SoundSticks 5 and restart Home Assistant.
4. Wake the speaker, then accept Bluetooth discovery or use Add integration.

### Manual

Copy `custom_components/soundsticks5` to `/config/custom_components/soundsticks5`, restart, and add the integration from Devices & services.

Home Assistant must have a connectable local Bluetooth adapter or a connectable Bluetooth proxy. Advertisement-only proxies cannot carry GATT commands.

## Optional SoundSticks Audio App

The App is intended for Home Assistant OS or Supervised installations, where Supervisor Apps and host D-Bus/audio sockets are available.

1. Settings → Apps → App store → Repositories.
2. Add `https://github.com/neqq3/soundsticks5-ha`.
3. Install **SoundSticks Audio**.
4. Start the App and inspect its log/`/health` page.
5. Put the speaker in Bluetooth pairing mode only for the initial pairing. Call `POST /scan`, then `POST /pair` with the chosen address, or configure an already-paired target. After pairing, normal wake does not require pairing mode.
6. In the SoundSticks integration options, enable Audio App and keep the default URL when App and HA share the host. Set the same API token in both places if used.

The App exposes port 8099 on the host network. Do not expose it to the public Internet. Use a non-empty API token on an untrusted LAN.

## Other HA installation types

- **Home Assistant Container/Core:** custom integration works, but Supervisor cannot install the bundled App. Run the `soundsticks5_audio` container yourself with system D-Bus, PulseAudio socket and BlueZ permissions, then set its reachable URL.
- **Remote BLE proxy:** BLE control may work. A2DP audio does not traverse an ESPHome Bluetooth proxy; the Audio App needs a Linux Bluetooth adapter local to its BlueZ host.
- **One adapter:** supported as the primary layout. Avoid separate scanning daemons that seize the same adapter. Hardware/driver limitations can still require tuning.

