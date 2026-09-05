"""Advertisement matching without treating a rotating BLE address as identity."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .const import CONTROL_SERVICE_UUID, FAST_PAIR_UUID, HARMAN_DISCOVERY_UUID


def matches_soundsticks5_advertisement(
    name: str | None,
    service_uuids: Sequence[str],
    service_data: Mapping[str, bytes],
) -> bool:
    """Return whether an advertisement is a safe SoundSticks 5 candidate.

    The private control service is normally visible only after connecting and
    enumerating GATT. Awake speakers instead advertise their model name and the
    Harman 0xFDDF service. Anonymous standby advertisements use the separately
    observed Fast Pair marker. Every candidate is still verified by GATT service
    enumeration before the coordinator sends a command.
    """
    normalized_uuids = {item.lower() for item in service_uuids}
    normalized_data = {key.lower(): bytes(value) for key, value in service_data.items()}

    if CONTROL_SERVICE_UUID in normalized_uuids:
        return True
    if "soundsticks 5" in (name or "").lower() and HARMAN_DISCOVERY_UUID in normalized_uuids:
        return True
    return not name and normalized_data.get(FAST_PAIR_UUID) == b"\x00\x00"
