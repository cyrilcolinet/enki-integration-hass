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

    @property
    def airflow_mode(self) -> str | None:
        value = self._data.get("airflow_mode")
        return str(value) if isinstance(value, str) else None

    @property
    def airflow_rotation(self) -> str | None:
        value = self._data.get("airflow_rotation")
        return str(value) if isinstance(value, str) else None

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

    @property
    def global_power(self) -> str | None:
        value = self._data.get("power")
        return str(value) if isinstance(value, str) else None

    @property
    def electrical_power(self) -> str | None:
        value = self._data.get("electrical_power")
        return str(value) if isinstance(value, str) else None

    @property
    def brightness(self) -> float | None:
        value = self._data.get("brightness")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @property
    def color_temperature(self) -> str | None:
        value = self._data.get("colorTemperature")
        return str(value) if isinstance(value, str) else None

    @property
    def hue(self) -> float | None:
        return _as_float(self._data.get("hue"))

    @property
    def saturation(self) -> float | None:
        return _as_float(self._data.get("saturation"))

    @property
    def color_mode(self) -> str | None:
        value = self._data.get("colorMode")
        return str(value) if isinstance(value, str) else None

    @property
    def power_production(self) -> float | None:
        value = self._data.get("power_production")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @property
    def shutter_position(self) -> int | None:
        from ..lib.shutter import normalize_shutter_position

        return normalize_shutter_position(self._data.get("shutter_position"))

    @property
    def shutter_opening(self) -> str | None:
        value = self._data.get("shutter_opening")
        return str(value).upper() if isinstance(value, str) else None

    @property
    def current_temperature(self) -> float | None:
        return _as_float(self._data.get("current_temperature"))

    @property
    def current_humidity(self) -> float | None:
        return _as_float(self._data.get("current_humidity"))

    @property
    def battery_health(self) -> str | None:
        value = self._data.get("battery_health")
        return str(value) if isinstance(value, str) else None

    @property
    def motion_detection(self) -> str | None:
        value = self._data.get("motion_detection") or self._data.get("motion_detector_state")
        return str(value) if isinstance(value, str) else None

    @property
    def vibration_detection(self) -> str | None:
        value = self._data.get("vibration_detection")
        return str(value) if isinstance(value, str) else None

    @property
    def contact_sensor_state(self) -> str | None:
        value = self._data.get("contact_sensor_state")
        return str(value) if isinstance(value, str) else None

    @property
    def vibration_detection_activation(self) -> str | None:
        value = self._data.get("vibration_detection_activation")
        return str(value) if isinstance(value, str) else None

    @property
    def contact_detection_activation(self) -> str | None:
        value = self._data.get("contact_detection_activation")
        return str(value) if isinstance(value, str) else None

    @property
    def vibration_sensibility_level(self) -> float | None:
        return _as_float(self._data.get("vibration_sensibility_level"))

    @property
    def siren_global_state(self) -> str | None:
        value = self._data.get("siren_global_state")
        return str(value) if isinstance(value, str) else None

    @property
    def water_sensor_state(self) -> str | None:
        value = self._data.get("water_sensor_state")
        return str(value) if isinstance(value, str) else None

    @property
    def pilot_wire_state(self) -> str | None:
        value = self._data.get("pilot_wire_state")
        return str(value) if isinstance(value, str) else None

    @property
    def thermostat_target_temperature(self) -> float | None:
        return _as_float(self._data.get("thermostat_target_temperature"))

    @property
    def thermostat_running_state(self) -> str | None:
        value = self._data.get("thermostat_running_state")
        return str(value) if isinstance(value, str) else None

    @property
    def window_open_detection(self) -> str | None:
        value = self._data.get("window_open_detection")
        return str(value) if isinstance(value, str) else None

    @property
    def window_open_detection_mode(self) -> str | None:
        value = self._data.get("window_open_detection_mode")
        return str(value) if isinstance(value, str) else None

    @property
    def occupancy(self) -> str | None:
        value = self._data.get("occupancy")
        return str(value) if isinstance(value, str) else None

    @property
    def occupancy_mode(self) -> str | None:
        value = self._data.get("occupancy_mode")
        return str(value) if isinstance(value, str) else None

    @property
    def electrical_endpoints(self) -> list[dict[str, Any]]:
        endpoints = self._data.get("electrical_endpoints")
        if isinstance(endpoints, list):
            return [endpoint for endpoint in endpoints if isinstance(endpoint, dict)]
        return []

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
