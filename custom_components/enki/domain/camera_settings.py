"""Settings of the meari-generation Lexman cameras (the solar camera, #216).

These cameras answer ``GET camera/{nodeId}/check-camera-status`` on the meari
service with every current setting in one payload, and take each change as
``POST camera/{nodeId}/change-…`` with ``{"value": …}``. The pre-meari IPC1xxKF
cameras have none of this (#165).

Choices and ranges come from the referentiel's ``possibleValues``, like the app
does; the fallbacks below are the app's own enums and only fill in when the
referentiel is silent. Light mode is left out until its values are pinned down.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# check-camera-status field → flat state key. Prefixed ``camera_`` because the
# payload's ``motionDetection`` is a *mode*, not the motion sensors' state.
_STATUS_FIELDS: dict[str, str] = {
    "nightVisionMode": "camera_night_vision_mode",
    "motionDetection": "camera_motion_detection_mode",
    "motionDetectionSensitivityLevel": "camera_motion_sensitivity",
    "humanFormDetectionSensitivityLevel": "camera_human_sensitivity",
    "indicatorLight": "camera_indicator_light",
    "flipScreenMode": "camera_flip_screen_mode",
    "recordingDuration": "camera_recording_duration",
    "batteryChargingStatus": "camera_battery_charging",
}
# Sent as numeric strings ("100", "52").
_NUMERIC_STRING_FIELDS: dict[str, str] = {
    "batteryLevel": "camera_battery_level",
    "wifiStrength": "camera_wifi_strength",
}


@dataclass(frozen=True)
class CameraSettingSpec:
    capability: str
    state_key: str
    translation_key: str


@dataclass(frozen=True)
class CameraSelectSpec(CameraSettingSpec):
    fallback_values: tuple[str, ...]


@dataclass(frozen=True)
class CameraSwitchSpec(CameraSettingSpec):
    on_value: str
    off_value: str


CAMERA_SELECTS: tuple[CameraSelectSpec, ...] = (
    CameraSelectSpec(
        "change_night_vision_mode",
        "camera_night_vision_mode",
        "camera_night_vision",
        ("SMART", "FULL_COLOR", "BLACK_AND_WHITE"),
    ),
    CameraSelectSpec(
        "change_motion_detection_mode",
        "camera_motion_detection_mode",
        "camera_motion_detection",
        ("ON", "OFF", "HUMAN_FORM"),
    ),
    CameraSelectSpec(
        "change_recording_duration",
        "camera_recording_duration",
        "camera_recording_duration",
        (
            "TEN_SECONDS",
            "TWENTY_SECONDS",
            "THIRTY_SECONDS",
            "FORTY_SECONDS",
            "ONE_MINUTE",
            "TWO_MINUTES",
            "THREE_MINUTES",
            "AUTO",
        ),
    ),
)

CAMERA_SWITCHES: tuple[CameraSwitchSpec, ...] = (
    CameraSwitchSpec(
        "change_indicator_light_mode",
        "camera_indicator_light",
        "camera_indicator_light",
        "ON",
        "OFF",
    ),
    CameraSwitchSpec(
        "change_flip_screen_mode",
        "camera_flip_screen_mode",
        "camera_flip_screen",
        "FLIP",
        "NOT_FLIP",
    ),
)

CAMERA_NUMBERS: tuple[CameraSettingSpec, ...] = (
    CameraSettingSpec(
        "change_motion_detection_sensitivity_level",
        "camera_motion_sensitivity",
        "camera_motion_sensitivity",
    ),
    CameraSettingSpec(
        "change_humanoid_detection_sensitivity_level",
        "camera_human_sensitivity",
        "camera_human_sensitivity",
    ),
)

CAMERA_SETTING_CAPABILITIES = frozenset(
    spec.capability for spec in (*CAMERA_SELECTS, *CAMERA_SWITCHES, *CAMERA_NUMBERS)
)


def parse_camera_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten check-camera-status into the state keys the entities read."""
    if not isinstance(payload, dict):
        return {}
    state: dict[str, Any] = {}
    for field, key in _STATUS_FIELDS.items():
        value = payload.get(field)
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            state[key] = value
    for field, key in _NUMERIC_STRING_FIELDS.items():
        value = payload.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            state[key] = value
        elif isinstance(value, str) and value.isdigit():
            state[key] = int(value)
    sd_card = payload.get("sdCard")
    if isinstance(sd_card, dict) and isinstance(sd_card.get("state"), str):
        state["camera_sd_state"] = sd_card["state"]
    return state


def select_values(spec: CameraSelectSpec, possible_values: dict[str, Any]) -> tuple[str, ...]:
    """Choices for a select: the referentiel's list, else the app's enum."""
    meta = possible_values.get(spec.capability)
    values = meta.get("values") if isinstance(meta, dict) else None
    if isinstance(values, list):
        listed = tuple(value for value in values if isinstance(value, str))
        if listed:
            return listed
    return spec.fallback_values


def number_range(
    spec: CameraSettingSpec, possible_values: dict[str, Any]
) -> tuple[float, float, float] | None:
    """(min, max, step) from the referentiel, or None when it gives no range."""
    meta = possible_values.get(spec.capability)
    range_meta = meta.get("range") if isinstance(meta, dict) else None
    if not isinstance(range_meta, dict):
        return None
    minimum, maximum = range_meta.get("min"), range_meta.get("max")
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        return None
    step = range_meta.get("step")
    return float(minimum), float(maximum), float(step) if isinstance(step, (int, float)) else 1.0
