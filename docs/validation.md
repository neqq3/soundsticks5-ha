# Validation status

## Automated

- confirmed AA/CMD/LEN/TLV encodings;
- light and aggregate state parsing;
- preservation of unknown `0x36` without assigning semantics;
- feedback-tone and auto-off parsing;
- seven-filter EQ framing and App-scale round-trip;
- malformed/range rejection;
- App configuration and local-source path restrictions;
- HTTP health/status/wake/release contracts;
- JSON/YAML, architecture matrix, syntax, lint, and amd64 Docker build in CI.

## Consumed from protocol research

Lighting, themes/default colors, linear sliders, speed, seven EQ bands/reset, feedback tone, five auto-off values, media actions, absolute volume, title/artist state, A2DP-connect wake, and release-to-AUX behavior use the current `soundsticks5-protocol` fact baseline.

## Implemented but hardware validation required

- App installation from a real HAOS/Supervised repository;
- pairing agent on a clean host;
- every declared container architecture;
- one adapter carrying BLE and A2DP under sustained use;
- WebSocket recovery across App restarts;
- stream reconnect/cleanup under network faults;
- final Alpine ffmpeg codec coverage;
- reconnect/release timing across firmware variants;
- current-stable Home Assistant frontend behavior.

Do not describe the audio App as broadly hardware-validated until these pass. A failure in the optional App does not establish a BLE integration failure, or vice versa.

