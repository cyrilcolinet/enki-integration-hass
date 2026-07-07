"""Capability-based Enki device detection (referentiel + BFF metadata)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..const import (
    DEVICE_TYPE_ACCESS_MOTORIZATION,
    DEVICE_TYPE_FANS,
    DEVICE_TYPE_INVERTERS,
    DEVICE_TYPE_LIGHTS,
    FAN_ENDPOINT,
)
from .models import EnkiDevice


def capabilities_set(capabilities: list[str] | dict[str, Any] | None) -> set[str]:
    """Normalize referentiel capabilities to a string set."""
    if isinstance(capabilities, list):
        return {capability for capability in capabilities if isinstance(capability, str)}
    if isinstance(capabilities, dict):
        return set(capabilities.keys())
    return set()


def possible_values_dict(possible_values: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(possible_values, dict):
        return possible_values
    return {}


def _supports(capabilities: set[str], possible_values: dict[str, Any], *names: str) -> bool:
    """True when any capability name appears in capabilities or possibleValues."""
    return any(name in capabilities or name in possible_values for name in names)


@dataclass(frozen=True, slots=True)
class EnkiCapabilityProfile:
    """Read-only view of what a physical Enki node can do.

    Built from referentiel metadata (authoritative for commands) and optional
    BFF dashboard fields (used for multi-endpoint outlets and solar tiles).
    """

    device_type: str
    capabilities: frozenset[str]
    possible_values: dict[str, Any]
    bff_device_type: str = ""
    main_change_capability_id: str | None = None
    main_change_capability_endpoints: tuple[int, ...] = ()
    power_production: float | None = None

    @classmethod
    def from_device(cls, device: EnkiDevice) -> EnkiCapabilityProfile:
        """Build a profile snapshot from a discovered device."""
        endpoints: list[int] = []
        for endpoint in device.main_change_capability_endpoints:
            if isinstance(endpoint, int):
                endpoints.append(endpoint)
            elif isinstance(endpoint, dict):
                endpoint_id = endpoint.get("id")
                if isinstance(endpoint_id, int):
                    endpoints.append(endpoint_id)
        return cls(
            device_type=device.device_type,
            capabilities=frozenset(capabilities_set(device.capabilities)),
            possible_values=possible_values_dict(device.possible_values),
            bff_device_type=device.bff_device_type,
            main_change_capability_id=device.main_change_capability_id,
            main_change_capability_endpoints=tuple(sorted(set(endpoints))),
            power_production=device.power_production,
        )

    # --- capability probes -------------------------------------------------

    @property
    def supports_light_state(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_light_state",
            "check_light_state",
        )

    @property
    def supports_electrical_power(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "switch_electrical_power",
            "check_electrical_power",
        )

    @property
    def supports_electrical_consumption(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_electrical_consumption",
            "total_supply_charge_consumption",
        )

    @property
    def supports_fan_speed(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_fan_speed",
            "check_fan_speed",
        )

    @property
    def supports_fan_speed_control(self) -> bool:
        """True when referentiel defines a fan speed range (CyrilP/hass-enki-component)."""
        return self.supports_fan_speed and self.fan_max_speed is not None

    @property
    def supports_fan_rotation(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_fan_rotation_direction",
            "check_fan_rotation_direction",
        )

    @property
    def supports_airflow_mode(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_airflow_mode",
            "check_airflow_mode",
        )

    @property
    def supports_power_production(self) -> bool:
        return "check_power_production" in self.capabilities

    @property
    def supports_shutter_position(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_shutter_position",
            "check_shutter_position",
        )

    @property
    def supports_shutter_opening(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_shutter_opening",
        )

    @property
    def supports_shutter_stop(self) -> bool:
        return "stop_change_shutter_position" in self.capabilities

    @property
    def supports_roller_shutter_state(self) -> bool:
        return "check_roller_shutter_state" in self.capabilities

    @property
    def supports_roller_shutter_mode(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_roller_shutter_mode",
            "check_roller_shutter_mode",
        )

    @property
    def supports_shutter_preset(self) -> bool:
        return "execute_preset" in self.capabilities

    @property
    def supports_current_temperature(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_current_temperature",
        )

    @property
    def supports_current_humidity(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_current_humidity",
        )

    @property
    def supports_battery_health(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_battery_health",
        )

    @property
    def supports_illuminance_level(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_illuminance_level",
        )

    @property
    def supports_motion_detection(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_motion_detection",
            "check_motion_detector_state",
        )

    @property
    def supports_vibration_detection(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_vibration_detection",
        )

    @property
    def supports_contact_sensor(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_contact_sensor_state",
        )

    @property
    def supports_vibration_detection_activation(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "activate_vibration_detection",
            "check_vibration_detection_activation",
        )

    @property
    def supports_contact_detection_activation(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "activate_contact_detection",
            "check_contact_detection_activation",
        )

    @property
    def supports_vibration_sensibility(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_vibration_sensibility_level",
            "check_vibration_sensibility_level",
        )

    @property
    def supports_siren(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "switch_siren_status",
            "check_siren_global_state",
        )

    @property
    def supports_water_leak(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_water_sensor_state",
        )

    @property
    def supports_pilot_wire(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "switch_pilot_wire_mode",
            "check_pilot_wire_state",
        )

    @property
    def supports_thermostat(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_thermostat_target_temperature",
            "check_thermostat_target_temperature",
        )

    @property
    def supports_window_open_detection(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_window_open_detection",
        )

    @property
    def supports_occupancy(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "check_occupancy",
        )

    @property
    def supports_window_open_detection_mode(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_window_open_detection_mode",
            "check_window_open_detection_mode",
        )

    @property
    def supports_occupancy_mode(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_occupancy_mode",
            "check_occupancy_mode",
        )

    @property
    def supports_color_temperature(self) -> bool:
        return _supports(
            self.capabilities,
            self.possible_values,
            "change_color_temperature",
            "check_color_temperature",
        )

    @property
    def supports_brightness_control(self) -> bool:
        return (
            _supports(
                self.capabilities,
                self.possible_values,
                "change_brightness",
                "check_brightness",
            )
            or self.supports_light_state
        )

    # --- HA platform classification ----------------------------------------

    @property
    def is_fan(self) -> bool:
        """Ceiling fans and VMC nodes (airflow-prod API)."""
        if self.device_type == DEVICE_TYPE_FANS:
            return True
        return self.supports_fan_speed or self.supports_fan_rotation or self.supports_airflow_mode

    @property
    def is_light_controllable(self) -> bool:
        """Lights, dimmers, and fan kits (not power-only outlets)."""
        if self.device_type == DEVICE_TYPE_LIGHTS:
            return True
        if self.is_fan:
            return self.supports_light_state
        if self.uses_power_api_only:
            return False
        return self.supports_light_state or self.supports_electrical_power

    @property
    def is_outlet(self) -> bool:
        """Power-only switches and outlets (Edisio, Equation relays, …)."""
        return self.uses_power_api_only

    @property
    def is_inverter(self) -> bool:
        """Solar inverters with live production on the BFF dashboard."""
        if self.device_type in {DEVICE_TYPE_INVERTERS, "inverters"}:
            return self.power_production is not None
        return self.supports_power_production and self.power_production is not None

    @property
    def is_cover(self) -> bool:
        """Roller shutters and similar motorizations (beta)."""
        if self.device_type in {DEVICE_TYPE_ACCESS_MOTORIZATION, "access_and_motorizations"}:
            return self.supports_shutter_position or self.supports_shutter_opening
        return self.supports_shutter_position

    @property
    def is_environment_sensor(self) -> bool:
        """Temperature, humidity, illuminance, or battery level sensors (not thermostats)."""
        if self.supports_thermostat:
            return (
                self.supports_current_humidity
                or self.supports_battery_health
                or self.supports_illuminance_level
            )
        return (
            self.supports_current_temperature
            or self.supports_current_humidity
            or self.supports_battery_health
            or self.supports_illuminance_level
        )

    @property
    def is_binary_sensor(self) -> bool:
        """Motion, contact, vibration, water leak, window, or occupancy detectors."""
        return (
            self.supports_motion_detection
            or self.supports_contact_sensor
            or self.supports_vibration_detection
            or self.supports_water_leak
            or self.supports_window_open_detection
            or self.supports_occupancy
        )

    @property
    def is_climate(self) -> bool:
        """Radiators and thermostats with a target temperature setpoint."""
        return self.supports_thermostat

    @property
    def is_pilot_wire(self) -> bool:
        """Pilot wire controllers (Comfort / Eco / Off)."""
        return self.supports_pilot_wire

    @property
    def is_roller_shutter_mode(self) -> bool:
        """Roller shutter wiring direction (normal / inverted)."""
        return self.is_cover and self.supports_roller_shutter_mode

    @property
    def is_config_switch(self) -> bool:
        """Detection activation toggles, sirens, and heating feature modes."""
        return (
            self.supports_vibration_detection_activation
            or self.supports_contact_detection_activation
            or self.supports_siren
            or self.supports_window_open_detection_mode
            or self.supports_occupancy_mode
        )

    @property
    def is_supported(self) -> bool:
        return (
            self.is_fan
            or self.is_light_controllable
            or self.is_outlet
            or self.is_inverter
            or self.is_cover
            or self.is_environment_sensor
            or self.is_binary_sensor
            or self.is_config_switch
            or self.is_climate
            or self.is_pilot_wire
            or self.supports_vibration_sensibility
        )

    @property
    def uses_power_api_only(self) -> bool:
        """Pure switches/outlets (e.g. Edisio) without the lighting API."""
        return self.supports_electrical_power and not self.supports_light_state

    @property
    def fan_max_speed(self) -> int | None:
        """Max non-off speed step from referentiel possibleValues."""
        speed_meta = self.possible_values.get("change_fan_speed") or self.possible_values.get(
            "check_fan_speed"
        )
        if isinstance(speed_meta, dict):
            speed_range = speed_meta.get("range")
            if isinstance(speed_range, dict):
                raw_max = speed_range.get("max")
                if isinstance(raw_max, (int, float)) and raw_max > 0:
                    return max(1, int(round(raw_max)))
        return None

    @property
    def power_switch_endpoints(self) -> list[int]:
        """BFF endpoints when mainChangeCapability is switch_electrical_power."""
        if self.main_change_capability_id != "switch_electrical_power":
            return []
        return list(self.main_change_capability_endpoints)

    @property
    def fan_light_endpoints(self) -> list[int]:
        """Light kit endpoints on ceiling fans (excludes the motor endpoint)."""
        if self.device_type != DEVICE_TYPE_FANS and not self.is_fan:
            return []
        return [endpoint for endpoint in self.power_switch_endpoints if endpoint != FAN_ENDPOINT]

    @property
    def fan_motor_endpoints(self) -> list[int]:
        """Power-prod endpoints that are not light kit circuits."""
        if self.main_change_capability_id != "switch_electrical_power":
            return []
        light_endpoints = set(self.fan_light_endpoints)
        return [
            endpoint for endpoint in self.power_switch_endpoints if endpoint not in light_endpoints
        ]

    @property
    def fan_motor_endpoint(self) -> int | None:
        """Single motor endpoint when unambiguous, else global power API."""
        motor_endpoints = self.fan_motor_endpoints
        if len(motor_endpoints) == 1:
            return motor_endpoints[0]
        return None


# --- Backward-compatible module functions (used by tests and legacy imports) ---


def supports_light_state(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    return _supports(capabilities, possible_values, "change_light_state", "check_light_state")


def supports_electrical_power(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    return _supports(
        capabilities,
        possible_values,
        "switch_electrical_power",
        "check_electrical_power",
    )


def supports_fan_speed(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    return _supports(capabilities, possible_values, "change_fan_speed", "check_fan_speed")


def supports_fan_speed_control(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    profile = EnkiCapabilityProfile(
        device_type=DEVICE_TYPE_FANS,
        capabilities=frozenset(capabilities),
        possible_values=possible_values,
    )
    return profile.supports_fan_speed_control


def supports_fan_rotation(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    return _supports(
        capabilities,
        possible_values,
        "change_fan_rotation_direction",
        "check_fan_rotation_direction",
    )


def supports_airflow_mode(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    return _supports(
        capabilities,
        possible_values,
        "change_airflow_mode",
        "check_airflow_mode",
    )


def supports_power_production(capabilities: set[str]) -> bool:
    return "check_power_production" in capabilities


def supports_shutter_position(capabilities: set[str], possible_values: dict[str, Any]) -> bool:
    return _supports(
        capabilities,
        possible_values,
        "change_shutter_position",
        "check_shutter_position",
    )


def is_cover_device(device: EnkiDevice) -> bool:
    return device.profile.is_cover


def device_capabilities(device: EnkiDevice) -> set[str]:
    return set(device.profile.capabilities)


def device_possible_values(device: EnkiDevice) -> dict[str, Any]:
    return device.profile.possible_values


def is_fan_device(device: EnkiDevice) -> bool:
    return device.profile.is_fan


def is_light_controllable(device: EnkiDevice) -> bool:
    return device.profile.is_light_controllable


def is_inverter_device(device: EnkiDevice) -> bool:
    return device.profile.is_inverter


def device_is_supported(device: EnkiDevice) -> bool:
    return device.profile.is_supported


def device_uses_power_api_only(device: EnkiDevice) -> bool:
    return device.profile.uses_power_api_only


def fan_max_speed(device: EnkiDevice) -> int | None:
    return device.profile.fan_max_speed


def main_change_capability_endpoints(device: EnkiDevice) -> list[int]:
    return device.profile.power_switch_endpoints


def fan_light_endpoints(device: EnkiDevice) -> list[int]:
    return device.profile.fan_light_endpoints
