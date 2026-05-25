"""Small helpers without Home Assistant imports (testable in isolation)."""

from __future__ import annotations

from typing import Any

from .const import FAN_SPEED_MAX

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
