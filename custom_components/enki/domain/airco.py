"""State of an Equation air conditioner (#286).

``equation-airco/{nodeId}/check-airconditioner-state`` answers the usual
``{nodeId, homeId, lastReportedDate, lastReportedValue}``, except
``lastReportedValue`` is an object rather than a scalar — the app calls it
``LastReportedStateApiModel`` and it mirrors, field for field, the body of
``change-airconditioner-state``::

    targetTemperature, currentTemperature, operatingMode, power, fanSpeed,
    selfCleanMode, frostProtectionMode, healthMode, quietMode, sleepMode,
    swingOrientation

So the device describes a full climate entity, not the ON/OFF switch the
integration exposes today. What the APK does not say is which values
``operatingMode``, ``fanSpeed`` and ``swingOrientation`` accept: the referentiel
publishes none of them. This flattens what comes back so it reaches diagnostics,
where a reporter's own unit can answer that before anything is built on a guess.
"""

from __future__ import annotations

from typing import Any

# Field in the API, state key here. Flat scalars only: a nested blob never
# reaches diagnostics, which is the whole point of reading this today.
_STATE_FIELDS = {
    "targetTemperature": "airco_target_temperature",
    "currentTemperature": "airco_current_temperature",
    "operatingMode": "airco_operating_mode",
    "power": "airco_power",
    "fanSpeed": "airco_fan_speed",
    "swingOrientation": "airco_swing_orientation",
    "selfCleanMode": "airco_self_clean_mode",
    "frostProtectionMode": "airco_frost_protection_mode",
    "healthMode": "airco_health_mode",
    "quietMode": "airco_quiet_mode",
    "sleepMode": "airco_sleep_mode",
}

AIRCO_STATE_KEYS = frozenset(_STATE_FIELDS.values())


def parse_airconditioner_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten check-airconditioner-state into the state keys diagnostics export."""
    if not isinstance(payload, dict):
        return {}
    reported = payload.get("lastReportedValue")
    if not isinstance(reported, dict):
        return {}
    return {
        key: reported[field]
        for field, key in _STATE_FIELDS.items()
        if isinstance(reported.get(field), (str, int, float, bool))
    }
