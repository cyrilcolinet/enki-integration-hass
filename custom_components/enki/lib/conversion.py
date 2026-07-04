"""Small helpers without Home Assistant imports (testable in isolation)."""

from __future__ import annotations

from typing import Any

from ..const import (
    AIRFLOW_ROTATION_CLOCKWISE,
    AIRFLOW_ROTATION_COUNTERCLOCKWISE,
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FAN_SPEED_MAX,
)

_ENKI_ROTATION_TO_DIRECTION: dict[str, str] = {
    AIRFLOW_ROTATION_CLOCKWISE: DIRECTION_FORWARD,
    AIRFLOW_ROTATION_COUNTERCLOCKWISE: DIRECTION_REVERSE,
    "COUNTER_CLOCKWISE": DIRECTION_REVERSE,
    "CCW": DIRECTION_REVERSE,
    "CW": DIRECTION_FORWARD,
    "FORWARD": DIRECTION_FORWARD,
    "REVERSE": DIRECTION_REVERSE,
    "SUMMER": DIRECTION_FORWARD,
    "WINTER": DIRECTION_REVERSE,
}

_DIRECTION_TO_ENKI_ROTATION: dict[str, str] = {
    DIRECTION_FORWARD: AIRFLOW_ROTATION_CLOCKWISE,
    DIRECTION_REVERSE: AIRFLOW_ROTATION_COUNTERCLOCKWISE,
}

# Home Assistant treats speed_count as the number of non-off speed steps.
# Percentage steps are 100 / speed_count (≈ 17 % per step for 6 speeds).


def speed_to_percentage(speed: int) -> int:
    """Map Enki fan speed (0–6) to a Home Assistant percentage (0–100)."""
    if speed <= 0:
        return 0
    return int(round(speed * 100 / FAN_SPEED_MAX))


def percentage_to_speed(percentage: int) -> int:
    """Map a Home Assistant percentage to an Enki fan speed (0–6)."""
    if percentage <= 0:
        return 0
    speed = int(round(percentage * FAN_SPEED_MAX / 100))
    return max(1, min(FAN_SPEED_MAX, speed))


def percentage_to_fan_speed(percentage: int, max_speed: int) -> int:
    """Map HA percentage to a fan speed level using the device max (0 = off)."""
    if percentage <= 0 or max_speed <= 0:
        return 0
    return max(0, min(max_speed, round(percentage * max_speed / 100)))


def fan_speed_to_percentage(speed: int, max_speed: int) -> int:
    """Map Enki fan speed to HA percentage (linear, matches CyrilP/hass-enki-component)."""
    if speed <= 0 or max_speed <= 0:
        return 0
    return int(round(speed * 100 / max_speed))


def normalize_power_state(last_reported: Any, endpoint: int) -> str:
    """Parse check-electrical-power lastReportedValue (string or per-endpoint map)."""
    if isinstance(last_reported, str):
        return last_reported
    if isinstance(last_reported, dict):
        for key in (str(endpoint), endpoint):
            if key in last_reported:
                value = last_reported[key]
                if isinstance(value, str):
                    return value
        if len(last_reported) == 1:
            value = next(iter(last_reported.values()))
            if isinstance(value, str):
                return value
    return "OFF"


def enki_rotation_to_direction(value: Any) -> str | None:
    """Map Enki rotation / season value to a Home Assistant fan direction."""
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("rotation", "rotationDirection", "bladeDirection", "direction", "mode"):
            if key in value:
                value = value[key]
                break
        else:
            return None
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return _ENKI_ROTATION_TO_DIRECTION.get(normalized)


def direction_to_enki_rotation(direction: str) -> str:
    """Map Home Assistant fan direction to an Enki rotation value."""
    mapped = _DIRECTION_TO_ENKI_ROTATION.get(direction)
    if mapped is None:
        raise ValueError(f"Unsupported fan direction: {direction}")
    return mapped


def select_light_color_modes(
    *, has_hs: bool, has_color_temp: bool, has_brightness: bool
) -> set[str]:
    """Pick the Home Assistant ``supported_color_modes`` set for an Enki light.

    Home Assistant forbids combining ``brightness`` or ``onoff`` with any real
    color mode (a color mode already implies brightness control), but it *does*
    allow combining ``hs`` and ``color_temp`` (a colour bulb that also does
    tunable white). Return the most capable valid set of ``ColorMode`` *value*
    strings.
    """
    color_modes: set[str] = set()
    if has_hs:
        color_modes.add("hs")
    if has_color_temp:
        color_modes.add("color_temp")
    if color_modes:
        return color_modes
    if has_brightness:
        return {"brightness"}
    return {"onoff"}


def hs_to_enki(hue: float, saturation: float) -> tuple[float, float]:
    """Convert HA HS (hue 0–360, sat 0–100) to Enki normalized 0–1 floats."""
    return round(hue / 360, 2), round(saturation / 100, 2)


def enki_to_hs(hue: Any, saturation: Any) -> tuple[float, float] | None:
    """Convert Enki normalized hue/saturation to HA HS. None if either is missing."""
    if hue is None or saturation is None:
        return None
    return round(float(hue) * 360, 2), round(float(saturation) * 100, 2)


def merge_light_state_payload(
    current: dict[str, Any],
    changes: dict[str, Any],
) -> dict[str, Any]:
    """Build a change-light-state body from the last reported value and requested changes.

    Enki requires the full lastReportedValue object on every POST. When turning ON,
    the API also expects ``power: ON`` even if the caller only asked for brightness
    or color temperature — otherwise Siroco+ kits ignore the command (#71).
    """
    payload = dict(current)
    if changes.get("power") == "OFF":
        payload.update(changes)
        return payload
    brightness = changes.get("brightness")
    if brightness is not None and float(brightness) <= 0:
        payload = dict(current)
        payload.update(changes)
        payload["power"] = "OFF"
        return payload
    payload["power"] = "ON"
    payload.update(changes)
    if "colorTemperature" in changes:
        payload["colorMode"] = "ct"
    return payload


def is_command_success_status(status: int) -> bool:
    """Enki command endpoints return 202 Accepted or 204 No Content."""
    return status in {202, 204}
