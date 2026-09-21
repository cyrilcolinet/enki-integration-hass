"""Fan preset, airflow mode, and rotation helpers."""

from __future__ import annotations

from .const import PRESET_MODE_BREEZE, PRESET_MODE_MANUAL
from .domain.models import EnkiDevice

# Enki API values (uppercase) ↔ Home Assistant preset slugs (lowercase).
ENKI_AIRFLOW_TO_PRESET: dict[str, str] = {
    "MANUAL": PRESET_MODE_MANUAL,
    "BREEZE": PRESET_MODE_BREEZE,
    "VENTILATION": "ventilation",
    "BOOST": "boost",
    "AUTO": "auto",
    "SLEEP": "sleep",
}

PRESET_TO_ENKI_AIRFLOW: dict[str, str] = {
    preset: enki for enki, preset in ENKI_AIRFLOW_TO_PRESET.items()
}

PRESET_MODE_ICONS: dict[str, str] = {
    PRESET_MODE_MANUAL: "mdi:fan",
    PRESET_MODE_BREEZE: "mdi:weather-windy",
    "ventilation": "mdi:fan-speed-2",
    "boost": "mdi:fan-plus",
    "auto": "mdi:fan-auto",
    "sleep": "mdi:sleep",
}


def device_supports_airflow_mode(device: EnkiDevice) -> bool:
    return device.profile.supports_airflow_mode


def device_supports_fan_rotation(device: EnkiDevice) -> bool:
    return device.profile.supports_fan_rotation


def enki_airflow_mode_to_preset(mode: str | None) -> str | None:
    """Map an Enki API airflow mode to a Home Assistant preset slug."""
    if mode is None:
        return None
    normalized = mode.strip().upper()
    if normalized in ENKI_AIRFLOW_TO_PRESET:
        return ENKI_AIRFLOW_TO_PRESET[normalized]
    lowered = mode.strip().lower()
    if lowered in PRESET_TO_ENKI_AIRFLOW:
        return lowered
    return lowered


def preset_to_enki_airflow_mode(preset: str) -> str:
    """Map a Home Assistant preset slug to an Enki API airflow mode."""
    lowered = preset.strip().lower()
    if lowered in PRESET_TO_ENKI_AIRFLOW:
        return PRESET_TO_ENKI_AIRFLOW[lowered]
    normalized = preset.strip().upper()
    if normalized in ENKI_AIRFLOW_TO_PRESET:
        return normalized
    raise ValueError(f"Unsupported preset mode: {preset}")


def preset_mode_icon(preset: str | None) -> str | None:
    """MDI icon for the active preset mode (entity icon in Home Assistant)."""
    if preset is None:
        return None
    return PRESET_MODE_ICONS.get(preset.strip().lower())


def airflow_modes_from_metadata(device: EnkiDevice) -> list[str]:
    """Return HA preset slugs advertised by the device referentiel."""
    possible = device.profile.possible_values
    meta = possible.get("change_airflow_mode") or possible.get("check_airflow_mode")
    if isinstance(meta, dict):
        values = meta.get("values")
        if isinstance(values, list):
            modes = [
                slug
                for value in values
                if isinstance(value, str)
                and (slug := enki_airflow_mode_to_preset(value)) is not None
            ]
            if modes:
                return modes
    return [PRESET_MODE_MANUAL, PRESET_MODE_BREEZE]


def infer_airflow_mode_supported(device: EnkiDevice, mode: str | None) -> bool:
    known = airflow_modes_from_metadata(device)
    if mode is not None:
        slug = enki_airflow_mode_to_preset(mode)
        if slug is not None and slug in known:
            return True
    return device_supports_airflow_mode(device)
