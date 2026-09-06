# Validation status

## Automated

- confirmed AA/CMD/LEN/TLV encodings and range rejection;
- lighting, aggregate media, feedback-tone, auto-off and EQ parsing;
- preservation of unknown `0x36` without assigning semantics;
- seven-filter EQ framing and App-scale round-trip;
- serialized refresh, explicit disconnect and bounded retry lifecycle;
- media action framing without optimistic playback-state fabrication;
- integration metadata and translations;
- lint, Python compilation, and tests on the oldest supported and current Home Assistant versions.

## Consumed from protocol research

Lighting, theme defaults and gradients, linear sliders, speed, seven EQ bands/reset, feedback tone, five auto-off values, media actions, absolute volume, title/artist state and the current App lifecycle findings use the `soundsticks5-protocol` fact baseline.

## Hardware validation still required

- one-click full refresh after every kind of external HK One change;
- explicit GATT release followed immediately by phone-App acquisition;
- playback toggle/readback against more A2DP source platforms;
- long-running behavior through different remote Bluetooth proxies;
- additional SoundSticks 5 regions, SKUs and firmware versions;

The archived A2DP/wake experiment is not a supported Home Assistant App and is excluded from the active validation matrix.
