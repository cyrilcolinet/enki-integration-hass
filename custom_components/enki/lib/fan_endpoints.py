"""Resolve fan motor vs light-kit endpoints on multi-endpoint ceiling fans."""

from __future__ import annotations

from typing import Any

from ..const import FAN_ENDPOINT

_FAN_METADATA_KEYS = ("type", "endpointType", "category", "role", "label")
_FAN_TYPE_MARKERS = frozenset({"fan", "motor", "ventilation", "vmc"})
_LIGHT_TYPE_MARKERS = frozenset({"light", "lighting", "dimmer", "lamp"})


def endpoint_id_from_entry(entry: int | dict[str, Any]) -> int | None:
    if isinstance(entry, int):
        return entry
    if isinstance(entry, dict):
        raw = entry.get("id")
        if isinstance(raw, int):
            return raw
    return None


def _normalize_marker(value: object) -> str:
    return str(value).strip().lower() if value is not None else ""


def motor_endpoints_from_metadata(
    endpoint_entries: tuple[int | dict[str, Any], ...],
) -> frozenset[int] | None:
    """Return motor endpoint IDs when BFF endpoint dicts carry type metadata."""
    motors: set[int] = set()
    lights: set[int] = set()
    for entry in endpoint_entries:
        ep_id = endpoint_id_from_entry(entry)
        if ep_id is None or not isinstance(entry, dict):
            continue
        marker = ""
        for key in _FAN_METADATA_KEYS:
            marker = marker or _normalize_marker(entry.get(key))
        if any(token in marker for token in _FAN_TYPE_MARKERS):
            motors.add(ep_id)
        elif any(token in marker for token in _LIGHT_TYPE_MARKERS):
            lights.add(ep_id)
    if motors:
        return frozenset(motors)
    if lights and len(lights) < len(endpoint_entries):
        all_ids = {
            endpoint_id_from_entry(entry)
            for entry in endpoint_entries
            if endpoint_id_from_entry(entry) is not None
        }
        return frozenset(all_ids - lights)
    return None


def _label_blob(*parts: str) -> str:
    return " ".join(part for part in parts if part).lower()


def infer_fan_motor_endpoints(
    *,
    power_endpoints: list[int],
    endpoint_entries: tuple[int | dict[str, Any], ...],
    supports_light_state: bool,
    supports_fan_speed: bool,
    device_name: str,
    referentiel_i18n: str,
    referentiel_model: str,
    reported_endpoint_ids: frozenset[int] = frozenset(),
) -> frozenset[int]:
    """Best-effort motor endpoint resolution (Siroco+ vs Inspire Radix, …)."""
    if not power_endpoints:
        return frozenset()

    from_metadata = motor_endpoints_from_metadata(endpoint_entries)
    if from_metadata is not None:
        return from_metadata

    # Speed-controlled fans drive the motor via change_fan_speed, so the motor
    # circuit never appears in the switch_electrical_power endpoint list. When
    # the electrical-power service still reports it (an endpoint id outside
    # power_endpoints), that unlisted endpoint is the motor and every switch
    # endpoint is a light kit. Separates the Inspire Cadix (AD_TCFL_1) dual
    # light layout — switch endpoints [1, 3], motor reported on the unlisted
    # endpoint 2 — from a Siroco+ motor-on-endpoint-1 layout, where the switch
    # list already covers every reported endpoint.
    if supports_fan_speed and reported_endpoint_ids:
        unlisted = reported_endpoint_ids - set(power_endpoints)
        if unlisted:
            return frozenset(unlisted)

    if not supports_light_state:
        return frozenset(power_endpoints)

    if len(power_endpoints) == 1:
        return frozenset(power_endpoints)

    sorted_eps = sorted(power_endpoints)
    labels = _label_blob(device_name, referentiel_i18n, referentiel_model)

    # Inspire Radix: dual LED kit at corners, motor on the middle endpoint.
    if (
        len(sorted_eps) == 3
        and supports_fan_speed
        and sorted_eps[2] - sorted_eps[0] == 2
        and "radix" in labels
    ):
        return frozenset({sorted_eps[1]})

    # Legacy Siroco+ / Cadix: motor on endpoint 1.
    if FAN_ENDPOINT in power_endpoints:
        return frozenset({FAN_ENDPOINT})

    return frozenset({min(power_endpoints)})


def fan_light_endpoints_from_motor(
    power_endpoints: list[int],
    motor_endpoints: frozenset[int],
) -> list[int]:
    return [endpoint for endpoint in power_endpoints if endpoint not in motor_endpoints]
