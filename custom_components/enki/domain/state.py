"""Typed accessors for Enki API last-reported device fields."""

from __future__ import annotations

from typing import Any


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _str_field(key: str) -> property:
    """A reported field that is only meaningful as a string; None otherwise."""

    def read(self: EnkiDeviceState) -> str | None:
        value = self._data.get(key)
        return value if isinstance(value, str) else None

    return property(read)


class EnkiDeviceState:
    """Read-only view of ``EnkiDevice.last_reported_value``.

    Centralises field names returned by different Enki micro-services so
    platform code does not scatter string keys across entities.
    """

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any] | None) -> None:
        self._data = data if isinstance(data, dict) else {}

    @property
    def raw(self) -> dict[str, Any]:
        """Underlying dict (same object as on the device — updates are live)."""
        return self._data

    @property
    def fan_speed(self) -> int | None:
        value = self._data.get("fan_speed")
        return int(value) if value is not None else None

    airflow_mode = _str_field("airflow_mode")

    airflow_rotation = _str_field("airflow_rotation")

    @property
    def airflow_rotation_supported(self) -> bool:
        return bool(self._data.get("airflow_rotation_supported"))

    @property
    def light_power(self) -> str | None:
        """Fan kit on/off — reported by lighting-prod, not power-prod."""
        value = self._data.get("light_power")
        if isinstance(value, str):
            return value
        return self.global_power

    camera_last_event_type = _str_field("camera_last_event_type")

    camera_last_event_at = _str_field("camera_last_event_at")

    camera_last_motion_at = _str_field("camera_last_motion_at")

    camera_last_sound_at = _str_field("camera_last_sound_at")

    camera_last_image_url = _str_field("camera_last_image_url")

    @property
    def camera_sd_removed(self) -> bool | None:
        value = self._data.get("camera_sd_removed")
        return bool(value) if isinstance(value, bool) else None

    global_power = _str_field("power")

    electrical_power = _str_field("electrical_power")

    @property
    def electrical_consumption(self) -> float | None:
        return _as_float(self._data.get("electrical_consumption"))

    electrical_consumption_unit = _str_field("electrical_consumption_unit")

    @property
    def brightness(self) -> float | None:
        value = self._data.get("brightness")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    color_temperature = _str_field("colorTemperature")

    @property
    def hue(self) -> float | None:
        return _as_float(self._data.get("hue"))

    @property
    def saturation(self) -> float | None:
        return _as_float(self._data.get("saturation"))

    color_mode = _str_field("colorMode")

    @property
    def power_production(self) -> float | None:
        value = self._data.get("power_production")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @property
    def energy_production(self) -> float | None:
        return _as_float(self._data.get("energy_production"))

    @property
    def shutter_position(self) -> int | None:
        from ..lib.shutter import normalize_shutter_position

        return normalize_shutter_position(self._data.get("shutter_position"))

    @property
    def shutter_opening(self) -> str | None:
        value = self._data.get("shutter_opening")
        return str(value).upper() if isinstance(value, str) else None

    @property
    def roller_shutter_state(self) -> str | None:
        value = self._data.get("roller_shutter_state")
        return str(value).upper() if isinstance(value, str) else None

    @property
    def roller_shutter_mode(self) -> str | None:
        value = self._data.get("roller_shutter_mode")
        return str(value).upper() if isinstance(value, str) else None

    @property
    def current_temperature(self) -> float | None:
        return _as_float(self._data.get("current_temperature"))

    @property
    def current_humidity(self) -> float | None:
        return _as_float(self._data.get("current_humidity"))

    @property
    def illuminance_level(self) -> float | None:
        return _as_float(self._data.get("illuminance_level"))

    battery_health = _str_field("battery_health")

    @property
    def motion_detection(self) -> str | None:
        value = self._data.get("motion_detection") or self._data.get("motion_detector_state")
        return str(value) if isinstance(value, str) else None

    vibration_detection = _str_field("vibration_detection")

    contact_sensor_state = _str_field("contact_sensor_state")

    vibration_detection_activation = _str_field("vibration_detection_activation")

    contact_detection_activation = _str_field("contact_detection_activation")

    @property
    def vibration_sensibility_level(self) -> float | None:
        return _as_float(self._data.get("vibration_sensibility_level"))

    siren_global_state = _str_field("siren_global_state")

    water_sensor_state = _str_field("water_sensor_state")

    pilot_wire_state = _str_field("pilot_wire_state")

    @property
    def thermostat_target_temperature(self) -> float | None:
        return _as_float(self._data.get("thermostat_target_temperature"))

    thermostat_running_state = _str_field("thermostat_running_state")

    window_open_detection = _str_field("window_open_detection")

    window_open_detection_mode = _str_field("window_open_detection_mode")

    @property
    def offset_temperature(self) -> float | None:
        return _as_float(self._data.get("offset_temperature"))

    child_lock = _str_field("child_lock")

    preheating_status = _str_field("preheating_status")

    occupancy = _str_field("occupancy")

    occupancy_mode = _str_field("occupancy_mode")

    @property
    def firmware_version(self) -> str | None:
        value = self._data.get("firmware_version") or self._data.get("version")
        return str(value) if isinstance(value, str) and value else None

    @property
    def firmware_latest_version(self) -> str | None:
        value = self._data.get("firmware_latest_version")
        return str(value) if isinstance(value, str) and value else None

    @property
    def firmware_update_available(self) -> bool | None:
        value = self._data.get("firmware_update_available")
        return value if isinstance(value, bool) else None

    firmware_update_status = _str_field("firmware_update_status")

    @property
    def node_connected(self) -> bool | None:
        value = self._data.get("node_connected")
        return value if isinstance(value, bool) else None

    @property
    def electrical_endpoints(self) -> list[dict[str, Any]]:
        endpoints = self._data.get("electrical_endpoints")
        if isinstance(endpoints, list):
            return [endpoint for endpoint in endpoints if isinstance(endpoint, dict)]
        return []

    def electrical_endpoint_ids(self) -> frozenset[int]:
        """Every endpoint id the electrical-power service reports for this node."""
        ids: set[int] = set()
        for endpoint in self.electrical_endpoints:
            raw = endpoint.get("id")
            if isinstance(raw, int):
                ids.add(raw)
        return frozenset(ids)

    def endpoint_power(self, endpoint_id: int) -> str | None:
        """Power state for one electrical endpoint (multi-gang switches)."""
        for endpoint in self.electrical_endpoints:
            if endpoint.get("id") != endpoint_id:
                continue
            last_reported = endpoint.get("lastReportedValue")
            if isinstance(last_reported, str):
                return last_reported
            if isinstance(last_reported, dict):
                power = last_reported.get("power")
                if isinstance(power, str):
                    return power
        return None

    def light_endpoints_have_mixed_power(self, endpoint_ids: list[int]) -> bool:
        """True when BFF endpoints disagree on ON/OFF (Siroco+ multi-light bug).

        Enki ignores turn_on when global power is already ON but endpoints differ.
        Sending OFF first forces a clean ON transition for all light endpoints.
        """
        if len(endpoint_ids) <= 1:
            return False

        power_values: set[str] = set()
        for endpoint in self.electrical_endpoints:
            if endpoint.get("id") not in endpoint_ids:
                continue
            last_reported = endpoint.get("lastReportedValue")
            if isinstance(last_reported, str) and last_reported in {"ON", "OFF"}:
                power_values.add(last_reported)
            elif isinstance(last_reported, dict):
                power = last_reported.get("power")
                if power in {"ON", "OFF"}:
                    power_values.add(power)
            if len(power_values) > 1:
                return True
        return False
