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
    "selfCleanMode": "airco_self_clean_mode",
    "frostProtectionMode": "airco_frost_protection_mode",
    "healthMode": "airco_health_mode",
    "quietMode": "airco_quiet_mode",
    "sleepMode": "airco_sleep_mode",
}

# `swingOrientation` is an object of two independent louvre settings, and they do
# not have the same number of steps: horizontal goes to 5, vertical to 4 (#286).
SWING_HORIZONTAL = ("AUTO", "NIV_1", "NIV_2", "NIV_3", "NIV_4", "NIV_5")
SWING_VERTICAL = ("AUTO", "NIV_1", "NIV_2", "NIV_3", "NIV_4")
_SWING_FIELDS = {
    "horizontal": "airco_swing_horizontal",
    "vertical": "airco_swing_vertical",
}

AIRCO_STATE_KEYS = frozenset({*_STATE_FIELDS.values(), *_SWING_FIELDS.values()})
# API field to state key, for a write that has to patch the cache back.
STATE_KEY_BY_FIELD = dict(_STATE_FIELDS)

# What the app's own enums allow. The referentiel publishes none of these, so
# they come from the decompiled app and are confirmed against a real unit
# reporting COOL / AUTO (#286).
OPERATING_MODES = ("AUTO", "COOL", "DRY", "FAN", "HEAT")
FAN_SPEEDS = ("AUTO", "LOW", "MEDIUM", "HIGH")


def build_airconditioner_payload(
    state: dict[str, Any],
    **changes: Any,
) -> dict[str, Any]:
    """The whole state back, with `changes` applied (#286).

    The app rebuilds the entire object on every write rather than sending the
    one field that moved, so writing a temperature alone would blank the mode,
    the fan speed and the four comfort toggles. `changes` keys are API names.
    """
    payload: dict[str, Any] = {
        field: state[key] for field, key in _STATE_FIELDS.items() if key in state
    }
    # Sending a null orientation would straighten louvres the user had set, so it
    # is rebuilt from what was read and only dropped when nothing was reported.
    swing = {field: state[key] for field, key in _SWING_FIELDS.items() if key in state}
    for field, key in _SWING_FIELDS.items():
        if key in changes:
            swing[field] = changes.pop(key)
    payload["swingOrientation"] = swing or None
    payload.update(changes)
    return payload


def parse_airconditioner_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten check-airconditioner-state into the state keys diagnostics export."""
    if not isinstance(payload, dict):
        return {}
    reported = payload.get("lastReportedValue")
    if not isinstance(reported, dict):
        return {}
    state = {
        key: reported[field]
        for field, key in _STATE_FIELDS.items()
        if isinstance(reported.get(field), (str, int, float, bool))
    }
    swing = reported.get("swingOrientation")
    if isinstance(swing, dict):
        state.update(
            {
                key: swing[field]
                for field, key in _SWING_FIELDS.items()
                if isinstance(swing.get(field), str)
            }
        )
    return state
