# SoundSticks Audio App

## API

All endpoints except `/health` require `Authorization: Bearer <token>` when `api_token` is configured.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | process/BlueZ health |
| GET | `/status` | pairing, connection, sink, playback, queue and volume state |
| GET/POST | `/scan` | scan for SoundSticks devices; optional `seconds` |
| POST | `/pair` | pair and trust; optional `address` |
| POST | `/connect` | connect Classic Bluetooth profiles |
| POST | `/disconnect`, `/release` | stop playback and release A2DP |
| POST | `/wake` | connect; accepts `keep_connected` and optional `delay` |
| POST | `/wake-release` | connect and schedule release |
| POST | `/play` | `url` or `path`, optional `title`, `enqueue`, and release policy |
| POST | `/pause`, `/resume`, `/stop` | transport control |
| POST | `/volume` | integer `volume` in `0..100` |
| GET | `/ws` | status and playback events |

```bash
curl http://homeassistant.local:8099/health
curl -X POST http://homeassistant.local:8099/wake-release -H 'Content-Type: application/json' -d '{"delay":3}'
curl -X POST http://homeassistant.local:8099/play -H 'Content-Type: application/json' -d '{"url":"https://example.invalid/tts.mp3"}'
```

Local paths are restricted to `/media`, `/share`, and `/data`. URL sources are passed to ffmpeg. WAV, MP3, AAC, FLAC, OGG and HTTP input support depends on the codecs/protocols included in Alpine ffmpeg.

If the A2DP pipeline disappears during playback and automatic reconnect is enabled, the App makes two bounded retries after BlueZ reconnects. A retry restarts the current item from the beginning; it does not claim sample-accurate stream resumption. The maximum playback duration defaults to six hours and is configurable to prevent abandoned processes.

## Options

- `adapter`: address, alias, or BlueZ adapter path component; empty chooses the first adapter.
- `device_address`: optional stable Classic Bluetooth address after pairing.
- `device_alias`: discovery name when no address is configured.
- `auto_connect`: connect a paired speaker at App startup.
- `auto_reconnect`: reconnect while active playback needs it.
- `release_after_playback` / `release_delay`: return control to AUX or another source.
- `sink_match`: case-insensitive PulseAudio sink substring.

Do not put a rotating BLE RPA in `device_address`; it is for the paired Classic Bluetooth identity shown by BlueZ.
