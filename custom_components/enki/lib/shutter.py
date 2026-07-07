"""Shutter position helpers (pure Python)."""

from __future__ import annotations


def normalize_shutter_position(value: object) -> int | None:
    """Convert Enki shutter position to an HA cover percentage (0 = closed, 100 = open)."""
    if isinstance(value, bool):
        return 100 if value else 0
    if isinstance(value, int):
        return max(0, min(100, value))
    if isinstance(value, float):
        return max(0, min(100, int(round(value))))
    return None


def shutter_opening_is_closed(value: object) -> bool | None:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized == "CLOSED":
            return True
        if normalized == "OPEN":
            return False
    return None


def roller_shutter_state_is_opening(value: object) -> bool | None:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized == "OPENING":
            return True
        if normalized in {"CLOSED", "OPEN", "CLOSING", "STOPPED", "STOP"}:
            return False
    return None


def roller_shutter_state_is_closing(value: object) -> bool | None:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized == "CLOSING":
            return True
        if normalized in {"CLOSED", "OPEN", "OPENING", "STOPPED", "STOP"}:
            return False
    return None


def roller_shutter_mode_options(possible_values: dict[str, object]) -> list[str]:
    """HA select slugs for change_roller_shutter_mode (lowercase)."""
    meta = possible_values.get("change_roller_shutter_mode") or possible_values.get(
        "check_roller_shutter_mode"
    )
    if isinstance(meta, dict):
        values = meta.get("values")
        if isinstance(values, list):
            return [str(value).lower() for value in values if isinstance(value, str)]
    return ["normal", "inverted"]


def roller_shutter_mode_api_value(option: str) -> str:
    return option.upper()


def roller_shutter_mode_option_slug(api_value: str) -> str:
    return api_value.lower()


def shutter_preset_options(possible_values: dict[str, object]) -> list[str]:
    """Preset identifiers from referentiel execute_preset metadata."""
    meta = possible_values.get("execute_preset")
    if not isinstance(meta, dict):
        return []
    values = meta.get("values")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str) and value]
