"""Advertisement matching without treating a rotating BLE address as identity."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from .const import CONTROL_SERVICE_UUID, FAST_PAIR_UUID, HARMAN_DISCOVERY_UUID

_ADDRESS_LIKE_NAME = re.compile(r"^(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}$", re.IGNORECASE)


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
    # BlueZ can report FDDF only as service data, with no service UUID list.
    # Requiring it in service_uuids drops a directly observed awake speaker.
    has_harman_service = (
        HARMAN_DISCOVERY_UUID in normalized_uuids or HARMAN_DISCOVERY_UUID in normalized_data
    )
    if "soundsticks 5" in (name or "").lower() and has_harman_service:
        return True
    # BlueZ/HA may expose the address as BLEDevice.name when the advertising
    # packet has no local name.  Treat both representations as anonymous.  A
    # connection is still verified against the private GATT service before any
    # command is sent.
    anonymous = not name or bool(_ADDRESS_LIKE_NAME.fullmatch(name))
    return anonymous and normalized_data.get(FAST_PAIR_UUID) == b"\x00\x00"
